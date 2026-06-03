# BioCred — Supabase Storage Policy Plan v1.0

**Status:** Draft for Alexander review. No buckets created yet.
**Owner:** Ainoa
**Last updated:** May 2026
**Scope:** Defines the two private buckets BioCred needs, the storage
RLS policies that protect them, and the signed-URL flow that lets
reviewers see uploaded documents without exposing them publicly.

This document covers the storage half of Block 1 / Block 2 wiring.
It pairs with `docs/production_migration_checklist_v1.md` (database
migration) and `database/supabase_rls.sql` (already in repo, table-level
policies). Storage policies in Supabase live in a separate
`storage.objects` table and need their own RLS rules.

---

## 1. Buckets

| Bucket             | Purpose                                                                 | Public? | Versioning | Default expiry of signed URLs |
|--------------------|-------------------------------------------------------------------------|---------|------------|-------------------------------|
| `credentials_docs` | Degrees, licences, certifications, permits, transcripts                 | private | enabled    | 10 minutes                    |
| `evidence_docs`    | Reference letters, project deliverables, field reports, awards          | private | enabled    | 10 minutes                    |

**No public bucket.** The pentagon/centroid renderer never needs raw
documents; it only consumes the JSON payload from
`render_payload_cache`. So no public read path exists for files.

If a future use case needs a logo or a profile photo to be public,
create a third bucket `public_assets` rather than relax these two.

### 1.1 Object naming convention

```
{profile_id}/{evidence_id_or_credential_id}/{yyyy-mm-dd}_{slug}.pdf
```

- `profile_id` is the `biologist_profile.id` UUID. Required first path
  segment so policies can match by `profile_id` directly.
- The full path is what gets stored in
  `credential_record.documentation_url` and
  `experience_evidence.evidence_source` (rename pending — see §6).

The first path segment **must** equal a profile UUID, because the
INSERT policy is anchored on that. Anything else is rejected.

### 1.2 File constraints

- Allowed MIME types: `application/pdf`, `image/jpeg`, `image/png`.
- Max size per object: 10 MiB. Configurable per bucket in Supabase.
- Encrypted at rest (default Supabase behaviour, AES-256).

---

## 2. Threat model in one paragraph

The thing we are protecting is the personal documentation a biologist
uploads to prove credentials. It contains names, addresses, signatures,
sometimes social-security adjacent identifiers (DOB, full school
records). The public registry is meant to publish *the fact that a
credential is verified*, not *the document itself*. So the rule is:

> The anonymous public must never receive bytes of any uploaded
> document, ever. Reviewers and admins receive bytes only via short-
> lived signed URLs minted by an Edge Function that re-checks role
> on every request.

Everything else flows from this.

---

## 3. Roles

Three identities access storage:

| Role            | DB role (`user_roles.role`) | Storage capabilities                    |
|-----------------|-----------------------------|-----------------------------------------|
| `biologist`     | `biologist`                 | INSERT into their own profile path; SELECT only their own; no DELETE |
| `reviewer`      | `reviewer`                  | SELECT for any profile in `pending_review` / `under_verification` / `verified` / `partial`; signed URL only |
| `admin`         | `admin`                     | All of reviewer + DELETE objects        |
| anon (public)   | _none_                      | nothing                                 |

The `is_reviewer_or_admin()` helper from `database/supabase_rls.sql`
is reused here, so storage and table policies share a single
authorisation predicate.

---

## 4. Storage RLS policies

These are the actual SQL statements. They go into
`database/storage_policies.sql` once approved. They run against the
internal `storage.objects` table that Supabase manages.

```sql
-- ============================================================
-- STORAGE: helper to extract profile_id from object path
-- Path is "{profile_id}/{credential_or_evidence_id}/{filename}"
-- ============================================================

CREATE OR REPLACE FUNCTION storage_profile_id(name TEXT)
RETURNS UUID AS $$
  SELECT NULLIF(split_part(name, '/', 1), '')::uuid
$$ LANGUAGE sql IMMUTABLE;

-- ============================================================
-- credentials_docs bucket
-- ============================================================

-- Biologist uploads only into their own profile folder
CREATE POLICY storage_credentials_owner_insert
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'credentials_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

-- Biologist can read their own
CREATE POLICY storage_credentials_owner_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

-- Reviewer / admin can read anything in this bucket
CREATE POLICY storage_credentials_reviewer_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND is_reviewer_or_admin()
);

-- Admin can delete (no biologist DELETE)
CREATE POLICY storage_credentials_admin_delete
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND has_role('admin')
);

-- No UPDATE policy: objects are immutable once stored.
-- Replacement = upload new path + update DB row to point to it.

-- ============================================================
-- evidence_docs bucket — same shape, different bucket_id
-- ============================================================

CREATE POLICY storage_evidence_owner_insert
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'evidence_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_evidence_owner_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_evidence_reviewer_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND is_reviewer_or_admin()
);

CREATE POLICY storage_evidence_admin_delete
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND has_role('admin')
);
```

Notes:

- There is **no** policy granting `SELECT` to the `anon` role on
  either bucket. That is the whole point.
- `INSERT` does not allow `UPDATE` — biologists cannot overwrite a
  document. To replace, upload to a new path and update the foreign
  key in the database. The old object stays for audit until an admin
  prunes it.
- `DELETE` is admin-only. This avoids reviewers nuking evidence and
  losing audit trail. Admins keep DELETE for GDPR-style data removal.

---

## 5. Signed-URL flow (reviewer download path)

Browsers must never carry a service-role key. Instead:

1. Reviewer opens the BioCred Review Portal and clicks a credential.
2. Portal calls Edge Function `generate_signed_url` with the
   credential row id (or evidence id).
3. Edge Function:
   1. Reads `auth.uid()` from the JWT in the request.
   2. Calls `is_reviewer_or_admin()` (Postgres function). If false,
      returns HTTP 403.
   3. Looks up `documentation_url` (or evidence path) for that row.
      If the path is null or does not exist, returns HTTP 404.
   4. Calls Supabase Storage `createSignedUrl(path, 600)` (10 minutes).
   5. Returns `{ url, expires_at }` to the portal.
4. Portal opens `url` in a new tab. The browser hits the URL directly.

The Edge Function:

- Is the **only** place a signed URL is minted.
- Is the **only** place that needs the service-role key.
- Logs each call to `verification_audit_log` with
  `change_reason = 'document_viewed'`. (Optional; nice for compliance.)

URL expiry is 10 minutes. After that the link is dead. Re-clicking
mints a fresh one. This means a leaked URL is dangerous for at most
10 minutes, and even then it points at one document, not a list.

---

## 6. Schema follow-ups touching storage

These are picked up by the production migration checklist; listed here
so they are visible to the storage owner:

- [ ] Add `credential_record.storage_path TEXT` (nullable). Replace
      `documentation_url` long-term — `documentation_url` is ambiguous
      between "URL of the doc" and "URL of the issuing authority".
- [ ] Add `experience_evidence.storage_path TEXT` (nullable). Today
      `evidence_source` is overloaded; split it into `storage_path`
      (file pointer) and `evidence_source_kind` (cv | reference |
      doc | etc).
- [ ] Backfill any seeded rows once the columns exist.

---

## 7. What anonymous browsers see

This is the answer to "could a curious user pull a PDF if they
guessed the URL?"

- Direct hit on `https://<project>.supabase.co/storage/v1/object/credentials_docs/<path>`
  → 403, regardless of guessability, because no policy grants `anon`
  read on this bucket.
- Direct hit using the anon key as bearer
  → 403, same reason.
- Direct hit using a leaked signed URL
  → 200 until the URL expires (≤ 10 minutes). After that, 410.

The pentagon/centroid renderer never reads from storage; it reads
the JSON payload from `render_payload_cache` via the
`public.profile_render_v1` view. Public read is **only** of computed
JSON, never of source documents.

---

## 8. Smoke tests (run before promoting to production)

These should live in `database/storage_smoke_test.sql` and a small
Node script in `tests/storage_smoke.js`. Each test prints PASS / FAIL.

- [ ] As anon: HEAD request on a known path returns 403.
- [ ] As biologist A: PUT into `<biologist_A_profile_id>/.../foo.pdf`
      succeeds. PUT into `<biologist_B_profile_id>/.../foo.pdf` fails.
- [ ] As biologist A: SELECT on biologist_A's own object succeeds.
      SELECT on biologist_B's object fails.
- [ ] As reviewer: SELECT on any object succeeds.
- [ ] As reviewer: DELETE on any object fails.
- [ ] As admin: DELETE succeeds.
- [ ] Signed-URL flow: Edge Function returns a URL for a reviewer
      JWT; same call with a biologist JWT returns 403.
- [ ] Signed URL minted at T returns 200 at T+5 min, 410 at T+11 min.

These are the same checks that should run in CI once the project
moves there.

---

## 9. Open questions for Alexander

1. Do we need 30-day automatic deletion of rejected documents, or do
   they stay forever? Default in this draft is "stay forever, admin
   prunes manually".
2. Should reviewers be allowed to leave annotations on a PDF (markup,
   redlines), or is the review limited to the row-level decision
   (verify/partial/reject + audit_notes)? Default in this draft is
   row-level only — no PDF markup, no per-page notes. PDFs are
   read-only artefacts.
3. Bucket region: keep both buckets in the same region as the
   Postgres project, or move evidence to a cheaper region? Default:
   same region, simpler ops.
4. Backups: Supabase keeps automatic backups of the database. Storage
   does **not** auto-snapshot in the same way. Do we want a nightly
   `s3 sync` to a Backblaze B2 bucket as cold backup, or accept the
   risk? Default in this draft: nightly B2 sync, ≤ $5/month.

---

## 10. Sign-off

- [ ] Alexander confirms §1 buckets, §2 threat model, §3 role table.
- [ ] Alexander chooses defaults in §9 questions 1–4.
- [ ] Ainoa runs §8 smoke tests on staging and posts results in this
      document under §11 Addenda.

## 11. Addenda

_(none yet)_
