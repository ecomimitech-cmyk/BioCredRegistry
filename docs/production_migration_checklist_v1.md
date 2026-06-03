# BioCred — Production Migration Checklist v1.0

**Status:** Draft for Alexander review. No commands run yet.
**Owner:** Ainoa
**Last updated:** May 2026
**Scope:** Move BioCred Registry from "core foundation built / prototype
complete" to "ready for production wiring", as scoped in Alexander's
May 2 review (Block 1 → 2 → 3).

This checklist is intentionally executable: every line that says
"Run …" should produce a verifiable artefact (file, row, RLS policy
listed in the Supabase dashboard, returning HTTP status, etc.). No
silent steps.

It pairs with `docs/storage_policy_plan_v1.md` (storage buckets) and
`docs/axis_contract_v1.md` (frozen axis contract). Do **not** start
Block 1 wiring until the axis contract test stays green.

Status legend:
- `[ ]` not started
- `[~]` in progress
- `[x]` done

---

## 0. Pre-flight (axis contract — Block 1 entry gate)

- [x] `pipeline/te_constants.py` exposes `AXIS_ORDER`,
      `PENTAGON_VISUAL_ORDER`, `PENTAGON_ORIENTATION` as the single
      source of truth.
- [x] `pipeline/pentagon_mapper.py` imports from `te_constants` and
      no longer redefines axis order.
- [x] `renderer/biocred-geometry.js` mirrors the Python constants
      and exposes `barycentricXY` keyed by axis name (no index zip).
- [x] `pipeline/tests/test_axis_contract.py` passes (28/28),
      including Node parity if `node` is on PATH.
- [x] Trajectory mapper bug (LOC ↔ SHS ↔ FAP ↔ RP swap) is fixed and
      regression-tested.
- [x] Visual centroid dot is rendered; `renderer/test_centroid_visual.js`
      asserts it lands at the geometric mean of the points.

If any of these regress, all later blocks are unsafe.

---

## 1. Supabase project provisioning

- [ ] Create production Supabase project (name `biocred-prod`,
      region close to most reviewers, US-east default).
- [ ] Create staging project (name `biocred-staging`) for the
      vertical slice. Same region, smallest tier.
- [ ] Record both project URLs and anon keys in 1Password (vault
      `BioCred Prod`). Service-role key stored only there; never
      committed.
- [ ] Add `.env.example` to repo root listing every variable name
      the wiring will need (no values).
- [ ] Pin Postgres engine version in dashboard; record it in this doc
      under "Environment fingerprint" §10.

## 2. Database migration order

Run on staging first, validate, then promote. Each step gets its own
transaction. If any fails, roll back and stop.

- [ ] **Step 2.1** — Apply `database/schema.sql` (core schema, ENUMs,
      tables, indexes, audit log, `update_updated_at` trigger). Expect
      4 tables, 8 ENUM types.
- [ ] **Step 2.2** — Apply `database/document_submissions.sql`
      (submission queue + reviewer fields).
- [ ] **Step 2.3** — Confirm `auth.users` is populated with at least
      one test user (Supabase Auth must be enabled).
- [ ] **Step 2.4** — Apply `database/supabase_rls.sql`. Expect:
      - `app_role` ENUM and `user_roles` table created.
      - Helper functions `auth_uid`, `has_role`, `is_reviewer_or_admin`.
      - RLS enabled on `biologist_profile`, `credential_record`,
        `experience_evidence`, `verification_audit_log`,
        `render_payload_cache`.
      - `can_submit_for_review` function compiles.
- [ ] **Step 2.5** — Verify all RLS is on:
      `SELECT relname, relrowsecurity FROM pg_class
       WHERE relname IN ('biologist_profile','credential_record',
       'experience_evidence','verification_audit_log',
       'render_payload_cache','user_roles');`
      All `relrowsecurity` must be `t`.
- [ ] **Step 2.6** — Seed one staging biologist + one reviewer in
      `user_roles`. Document the UUIDs in the staging runbook.

## 3. Schema gaps to close before vertical slice

These were flagged by Alexander on May 2. They are **not** prototype
issues — they will break the vertical slice if shipped as-is.

- [ ] **registry_id ↔ profile_id lookup.**
      Public profile pages receive `registry_id` (human-readable),
      but `render_payload_cache.profile_id` is a UUID. Add a public
      view `public.profile_render_v1` that resolves
      `registry_id → render_payload_json`, scoped to verified active
      profiles only. Webflow JS hits the view, never the cache table.
- [ ] **`experience_evidence.is_verified` vs row-level
      `verification_status`.** Today the schema uses a boolean while
      `credential_record` and `biologist_profile` use the
      `verification_status` ENUM. Either:
      a) add `verification_status` ENUM column and deprecate `is_verified`,
      mirrored via trigger;
      b) keep boolean and document as the single source of truth.
      Decision: option (a). Add migration `database/2026_05_evidence_verification_status.sql`.
- [ ] **Audit log triggers.** Today, audit rows are written by
      whatever code reviews credentials. Add an `AFTER UPDATE`
      trigger on `biologist_profile`, `credential_record`, and
      `experience_evidence` that auto-inserts into
      `verification_audit_log` whenever `verification_status` changes.
- [ ] **Verified-record edit lock.** Add a `BEFORE UPDATE` trigger
      that rejects column changes (other than `verification_status`,
      `audit_notes`, `updated_at`) when a row is currently `verified`.
      Editing a verified credential should require a re-review path,
      not a silent overwrite.

Acceptance: a reviewer can flip `verification_status` from
`pending_review → verified` and a row appears in `verification_audit_log`
with the previous status, the new status, and `changed_by = auth.uid()`,
without any application code touching the audit table.

## 4. Public-safe data exposure

Webflow embeds and the public profile page must never query private
tables directly. Options, in preference order:

- [ ] **Option A (preferred).** Add Postgres views in schema `public`
      that expose only verified active rows; revoke direct table
      grants. Concrete views to create:
      - `public.profile_public_v1` — biologist_profile fields safe to expose.
      - `public.credential_public_v1` — verified credentials only.
      - `public.evidence_public_v1` — `verification_status = verified` only,
        no internal review notes.
      - `public.profile_render_v1` — joins render_payload_cache by
        `registry_id`, only when profile is active+verified.
      Grant `SELECT` to `anon`, `authenticated`. Keep the underlying
      tables hidden.
- [ ] **Option B.** Edge Functions that serve the same data. More
      flexibility, more moving parts. Defer unless a use case forces it.

## 5. Storage wiring

See `docs/storage_policy_plan_v1.md` for the policies. This checklist
just lists the operational steps:

- [ ] Create bucket `credentials_docs` (private, no public list).
- [ ] Create bucket `evidence_docs` (private, no public list).
- [ ] Apply Storage RLS from `storage_policy_plan_v1.md` §4.
- [ ] Confirm signed-URL generation works only via Edge Function
      `generate_signed_url`, not from the browser anon key.
- [ ] Run smoke test: as biologist, upload a 1-page PDF, confirm row
      lands in `experience_evidence`. As anonymous viewer, confirm
      the file is NOT downloadable via direct URL.

## 6. Vertical slice acceptance criteria (Block 2 entry gate)

A single end-to-end vertical slice must succeed before Block 3
(public profile wiring) starts.

- [ ] One test biologist (`registry_id = BCR-VS-001`) in staging.
- [ ] Biologist logs in, uploads one PDF degree certificate via the
      upload page, sees `verification_status = submitted`.
- [ ] Reviewer logs in, opens reviewer queue, sees the new row.
- [ ] Reviewer downloads the PDF via signed URL (not a direct bucket URL).
- [ ] Reviewer flips status to `verified` with a note. Audit row appears.
- [ ] `render_payload_cache` row regenerates automatically (Edge
      Function `regenerate_render_payload`, triggered post-verify).
- [ ] Public profile page `https://staging.biocredregistry.com/p/BCR-VS-001`
      loads via `public.profile_render_v1` and displays the
      pentagon/centroid using live data only.
- [ ] Anonymous viewer cannot download the PDF directly.
- [ ] `pipeline/tests/test_axis_contract.py` still passes.

## 7. Render payload regeneration

- [ ] Add Edge Function `regenerate_render_payload(profile_id uuid)`
      that:
      1) reads all `experience_evidence` rows for the profile that
         are currently `verified`,
      2) runs them through the Translation Engine (TE_v1.0),
      3) computes `render_payload_json` (axis-keyed dicts, never lists,
         per `axis_contract_v1.md` §5),
      4) upserts into `render_payload_cache` keyed by
         `(profile_id, translation_version)`.
- [ ] Add post-update DB trigger that calls the Edge Function whenever
      a verified evidence row changes (insert / update / delete).
- [ ] Manual force-regen endpoint for admins.

## 8. Naming changes (Alexander's request, May 2)

- [ ] Rename "Agency Review Portal" → "BioCred Review Portal" in:
      - `frontend/agency_review_v1.html` (file + heading)
      - `docs/onboarding_workflow_v1.md`
      - `README.md`
      - `TODO.md`
      - any in-repo doc that mentions it.
- [ ] Add a one-paragraph note in the public landing page draft that
      BioCred is **not** a government or licensing agency.

## 9. Build-checklist language overhaul

Replace status labels per Alexander's wording (May 2):

- "Complete / no rework needed" → use one of:
  - "Core foundation built"
  - "Ready for production wiring"
  - "Prototype complete"
  - "Requires live integration"
  - "Requires production hardening"

Apply to `docs/biocred_build_checklist_v1.html`, `README.md`, `TODO.md`.
This is documentation only — no code change needed.

## 10. Environment fingerprint

Fill in once the projects are provisioned. Future migrations diff
against this.

| Field                 | Staging | Production |
|-----------------------|---------|------------|
| Supabase project URL  |         |            |
| Postgres version      |         |            |
| Auth provider(s)      |         |            |
| Bucket names          |         |            |
| Edge Function runtime |         |            |
| Domain                |         |            |
| First migration date  |         |            |

## 11. Rollback plan

If Block 2's vertical slice produces a critical issue (data leak,
RLS bypass, signed-URL leak, audit drift), the rollback is:

1. Disable the public domain via DNS (point Webflow to a maintenance
   page).
2. Revoke the anon key in Supabase dashboard, rotate to a new key
   (this immediately invalidates any leaked URL).
3. Take the staging Supabase project read-only by revoking
   `anon` and `authenticated` grants on every public view.
4. Restore from automatic backup if data integrity is in question.
5. File a post-mortem note in `CHANGELOG.md` under a `### Rollback`
   subsection with date, scope, and resolution.

## 12. Sign-off

- [ ] Alexander confirms the language in §9 is acceptable.
- [ ] Alexander confirms the rename in §8 is final.
- [ ] Ainoa confirms the axis contract test stays green after every
      step in §1–§7.
- [ ] Both confirm the vertical slice acceptance criteria in §6 are
      the right gate to Block 3.

Once all three checkboxes are signed, this document promotes from
"draft for review" to "v1.0 locked" and any change must be a §13
addendum.

## 13. Addenda

_(none yet)_
