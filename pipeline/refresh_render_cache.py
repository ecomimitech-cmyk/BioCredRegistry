"""
BioCred M4 — refresh render_payload_cache from live data.

The translation engine is the single source of truth for axis weights and it
stays in Python, so this job is the bridge that has never existed: read approved
profiles out of the database, run them through the engine, write the payload back
into the cache the public profile reads from.

Staleness needs no extra table. A profile's cache row is stale when it is missing
or older than the profile's `updated_at`, and `review_decide()` touches
`updated_at` on every decision — so approving a profile marks it for recompute
as a side effect of the decision itself.

Usage
-----
    export SUPABASE_URL=https://<ref>.supabase.co
    export SUPABASE_SERVICE_ROLE_KEY=<service_role key>

    python3 -m pipeline.refresh_render_cache --dry-run
    python3 -m pipeline.refresh_render_cache
    python3 -m pipeline.refresh_render_cache --all
    python3 -m pipeline.refresh_render_cache --selftest   # no database needed

The service_role key bypasses RLS, which is why this runs server-side and never
in a browser. Keep it in the environment, never in the repo.
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from pipeline.te_constants import TRANSLATION_VERSION
from pipeline.translation_engine import translate_profile

PUBLISHABLE_STATUSES = ("verified", "partial")

PROFILE_COLUMNS = ("id,registry_id,full_name,professional_title,organization,state,"
                   "city,primary_discipline,years_experience,verification_status,"
                   "visibility_status,updated_at")
EVIDENCE_COLUMNS = ("id,profile_id,domain_category,activity_type,species_or_system,"
                    "habitat_context,project_type,years_applied,role_level,"
                    "evidence_source,verification_status")
CREDENTIAL_COLUMNS = "id,profile_id,verification_status"
CACHE_COLUMNS = "profile_id,render_payload_hash,generated_at,translation_version"


# ─── transport A: PostgREST with a service_role key ──────────────────────

class RestClient:
    """The production shape. Needs SUPABASE_SERVICE_ROLE_KEY."""

    label = "PostgREST"

    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    def _request(self, method, path, query=None, body=None, extra_headers=None):
        target = self.url + path
        if query:
            target += "?" + urllib.parse.urlencode(query, safe="().,*")
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "apikey": self.key,
            "Authorization": "Bearer " + self.key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(target, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                raw = res.read().decode()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as err:
            detail = err.read().decode()[:400]
            raise RuntimeError(
                "%s %s failed (%s): %s" % (method, path, err.code, detail)
            ) from None

    def _select(self, table, query):
        return self._request("GET", "/rest/v1/" + table, query=query) or []

    def publishable_profiles(self):
        return self._select("biologist_profile", {
            "select": PROFILE_COLUMNS,
            "visibility_status": "eq.active",
            "verification_status": "in.(%s)" % ",".join(PUBLISHABLE_STATUSES),
        })

    def _by_profile(self, table, columns, ids):
        return self._select(table, {
            "select": columns,
            "profile_id": "in.(%s)" % ",".join(ids),
        })

    def evidence_for(self, ids):
        return self._by_profile("experience_evidence", EVIDENCE_COLUMNS, ids)

    def credentials_for(self, ids):
        return self._by_profile("credential_record", CREDENTIAL_COLUMNS, ids)

    def cache_for(self, ids):
        return self._select("render_payload_cache", {
            "select": CACHE_COLUMNS,
            "profile_id": "in.(%s)" % ",".join(ids),
            "translation_version": "eq." + TRANSLATION_VERSION,
        })

    def upsert_cache(self, rows):
        self._request(
            "POST", "/rest/v1/render_payload_cache",
            query={"on_conflict": "profile_id,translation_version"},
            body=rows,
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )


# ─── transport B: psql against the database directly ─────────────────────

class PsqlClient:
    """Fallback for running this from an admin machine.

    Deliberately offered because it avoids putting a service_role key — which
    bypasses every RLS policy in the project — into another environment. It uses
    the database credentials an operator already holds. `psql` reads the password
    from PGPASSWORD or ~/.pgpass as usual; nothing is passed on the command line.
    """

    label = "psql"

    def __init__(self, dsn, psql="psql"):
        self.dsn = dsn
        self.psql = psql

    def _run(self, sql, expect_json=True):
        proc = subprocess.run(
            [self.psql, self.dsn, "-At", "-v", "ON_ERROR_STOP=1", "-c", sql],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError("psql failed: " + proc.stderr.strip()[:400])
        if not expect_json:
            return None
        out = proc.stdout.strip()
        return json.loads(out) if out and out != "" else []

    def _select_json(self, inner_sql):
        return self._run(
            "SELECT coalesce(json_agg(t), '[]'::json) FROM (%s) t" % inner_sql
        )

    @staticmethod
    def _id_list(ids):
        return ",".join("'" + i.replace("'", "''") + "'" for i in ids)

    def publishable_profiles(self):
        return self._select_json(
            "SELECT %s FROM biologist_profile WHERE visibility_status = 'active' "
            "AND verification_status IN (%s)" % (
                PROFILE_COLUMNS,
                ",".join("'%s'" % s for s in PUBLISHABLE_STATUSES),
            )
        )

    def evidence_for(self, ids):
        return self._select_json(
            "SELECT %s FROM experience_evidence WHERE profile_id IN (%s)"
            % (EVIDENCE_COLUMNS, self._id_list(ids))
        )

    def credentials_for(self, ids):
        return self._select_json(
            "SELECT %s FROM credential_record WHERE profile_id IN (%s)"
            % (CREDENTIAL_COLUMNS, self._id_list(ids))
        )

    def cache_for(self, ids):
        return self._select_json(
            "SELECT %s FROM render_payload_cache WHERE profile_id IN (%s) "
            "AND translation_version = '%s'"
            % (CACHE_COLUMNS, self._id_list(ids), TRANSLATION_VERSION)
        )

    def upsert_cache(self, rows):
        # JSON is dollar-quoted with a tag that cannot appear in JSON text, so
        # quoting inside the payload can't terminate the literal early.
        tag = "$bcpayload$"
        statements = []
        for row in rows:
            payload = json.dumps(row["render_payload_json"], separators=(",", ":"))
            statements.append(
                "INSERT INTO render_payload_cache (profile_id, render_payload_json, "
                "render_payload_hash, translation_version, generated_at) VALUES "
                "('%s', %s%s%s::jsonb, '%s', '%s', '%s') "
                "ON CONFLICT (profile_id, translation_version) DO UPDATE SET "
                "render_payload_json = EXCLUDED.render_payload_json, "
                "render_payload_hash = EXCLUDED.render_payload_hash, "
                "generated_at = EXCLUDED.generated_at;" % (
                    row["profile_id"], tag, payload, tag,
                    row["render_payload_hash"], row["translation_version"],
                    row["generated_at"],
                )
            )
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as fh:
            fh.write("BEGIN;\n" + "\n".join(statements) + "\nCOMMIT;\n")
            path = fh.name
        try:
            proc = subprocess.run(
                [self.psql, self.dsn, "-v", "ON_ERROR_STOP=1", "-f", path],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode != 0:
                raise RuntimeError("psql upsert failed: " + proc.stderr.strip()[:400])
        finally:
            os.unlink(path)


# ─── payload ─────────────────────────────────────────────────────────────

def build_payload(profile, evidence, credentials):
    """Engine output plus the display metadata the public page needs.

    The engine's own keys are canonical — it is the tested implementation of the
    axis contract. `profile_meta` is added on top for presentation only; nothing
    in it feeds the pentagon.
    """
    payload = translate_profile(evidence, profile)

    verified_evidence = [
        e for e in evidence if e.get("verification_status") in PUBLISHABLE_STATUSES
    ]
    verified_credentials = [
        c for c in credentials if c.get("verification_status") in PUBLISHABLE_STATUSES
    ]

    payload["profile_meta"] = {
        "display_name": profile.get("full_name") or "",
        "professional_title": profile.get("professional_title") or "",
        "organization": profile.get("organization") or "",
        "state": profile.get("state") or "",
        "city": profile.get("city") or "",
        "primary_discipline": profile.get("primary_discipline") or "",
        "verification_status": profile.get("verification_status"),
        "verified_experience_records": len(verified_evidence),
        "verified_credential_records": len(verified_credentials),
    }
    return payload


def payload_hash(payload):
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


# ─── main flow ───────────────────────────────────────────────────────────

def is_stale(profile, cache_row):
    if cache_row is None:
        return True
    generated = cache_row.get("generated_at")
    updated = profile.get("updated_at")
    if not generated or not updated:
        return True
    return generated < updated


def run(client, refresh_all=False, dry_run=False):
    print("Transport: %s\n" % client.label)
    profiles = client.publishable_profiles()

    if not profiles:
        print("No publishable profiles. Nothing to do.")
        return 0

    ids = [p["id"] for p in profiles]
    evidence_rows = client.evidence_for(ids)
    credential_rows = client.credentials_for(ids)
    cache_rows = client.cache_for(ids)

    evidence_by = {}
    for row in evidence_rows:
        evidence_by.setdefault(row["profile_id"], []).append(row)
    credentials_by = {}
    for row in credential_rows:
        credentials_by.setdefault(row["profile_id"], []).append(row)
    cache_by = {row["profile_id"]: row for row in cache_rows}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pending = []
    skipped = 0

    for profile in profiles:
        cache_row = cache_by.get(profile["id"])
        if not refresh_all and not is_stale(profile, cache_row):
            skipped += 1
            continue

        payload = build_payload(
            profile,
            evidence_by.get(profile["id"], []),
            credentials_by.get(profile["id"], []),
        )
        digest = payload_hash(payload)

        if cache_row and cache_row.get("render_payload_hash") == digest:
            # Stale by timestamp but identical in content — touch it and move on.
            skipped += 1
            continue

        units = len(payload.get("evidence_units", []))
        print("  %-10s %-28s %2d evidence units  %s" % (
            profile.get("registry_id"), (profile.get("full_name") or "")[:28], units, digest[:12]
        ))
        pending.append({
            "profile_id": profile["id"],
            "render_payload_json": payload,
            "render_payload_hash": digest,
            "translation_version": TRANSLATION_VERSION,
            "generated_at": now,
        })

    print("\n%d publishable, %d up to date, %d to write." % (len(profiles), skipped, len(pending)))

    if not pending:
        return 0
    if dry_run:
        print("Dry run — nothing written.")
        return 0

    client.upsert_cache(pending)
    print("Wrote %d payload(s)." % len(pending))
    return len(pending)


# ─── self test (no database) ─────────────────────────────────────────────

def selftest():
    """Prove the engine path works without needing staging access."""
    profile = {
        "registry_id": "TEST01",
        "full_name": "Test Profile",
        "professional_title": "Field Biologist",
        "organization": "Nowhere",
        "state": "California",
        "city": "Davis",
        "primary_discipline": "Wildlife",
        "verification_status": "verified",
    }
    evidence = [
        {"id": "e1", "domain_category": "field_experience",
         "activity_type": "avian point count survey", "species_or_system": "passerines",
         "years_applied": 5, "role_level": "lead", "verification_status": "verified"},
        {"id": "e2", "domain_category": "regulatory_experience",
         "activity_type": "CEQA compliance monitoring", "years_applied": 3,
         "role_level": "contributor", "verification_status": "verified"},
        {"id": "e3", "domain_category": "field_experience",
         "activity_type": "bat capture and handling", "species_or_system": "myotis",
         "years_applied": 2, "role_level": "participant", "verification_status": "rejected"},
    ]
    credentials = [{"id": "c1", "verification_status": "verified"}]

    payload = build_payload(profile, evidence, credentials)
    units = payload["evidence_units"]

    print("translation_version :", payload.get("translation_version"))
    print("biologist_id        :", payload.get("biologist_id"))
    print("hash                :", payload_hash(payload))
    print("verified counts     : %d evidence, %d credentials" % (
        payload["profile_meta"]["verified_experience_records"],
        payload["profile_meta"]["verified_credential_records"],
    ))
    print("\nunits produced, by source record:")
    per_source = {}
    for unit in units:
        per_source.setdefault(unit["source_ref"]["evidence_id"], []).append(unit)
    for source in ("e1", "e2", "e3"):
        made = per_source.get(source, [])
        note = ""
        if source == "e3":
            note = "  ← rejected, correctly excluded"
        elif len(made) > 1:
            note = "  ← split: the activity is both field and regulatory"
        print("  %s → %d unit(s)%s" % (source, len(made), note))

    problems = []
    if any(u["source_ref"]["evidence_id"] == "e3" for u in units):
        problems.append("a rejected record reached the payload")
    for unit in units:
        total = sum(unit["domain_weights"].values())
        if abs(total - 1.0) > 0.01:
            problems.append("weights sum to %.4f, not 1.0" % total)
        if not (0.10 <= unit["intensity_weight"] <= 1.30):
            problems.append("intensity %.3f out of range" % unit["intensity_weight"])

    if problems:
        print("\nFAIL:")
        for p in problems:
            print("  -", p)
        return 1
    print("\nSelf test passed: weights normalise, intensities in range, rejected excluded.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="compute but write nothing")
    parser.add_argument("--all", action="store_true", help="recompute even if not stale")
    parser.add_argument("--selftest", action="store_true", help="run the engine offline")
    parser.add_argument("--dsn", help="Postgres connection string; uses psql instead "
                                      "of a service_role key")
    parser.add_argument("--psql", default=os.environ.get("PSQL_BIN", "psql"),
                        help="path to the psql binary")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    dsn = args.dsn or os.environ.get("BIOCRED_DSN")
    if dsn:
        client = PsqlClient(dsn, psql=args.psql)
    else:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            print("Give either --dsn / BIOCRED_DSN, or SUPABASE_URL and "
                  "SUPABASE_SERVICE_ROLE_KEY.", file=sys.stderr)
            return 2
        client = RestClient(url, key)

    run(client, refresh_all=args.all, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
