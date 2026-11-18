# BioCred Milestone 2 — Review Package

**For:** Alexander Funk · **From:** Ainoa Figueroa Vidal · **Date:** 26 Aug 2026
**Environment:** `biocred-staging` — `https://wmwzqnzyhiyhfzncuxkc.supabase.co`
**Milestone:** M2 *Evidence intake* — working intake for profiles, credentials, documents, experience records

This is the written half of the review package. The Loom shows each line below
happening on screen, in this order, in one continuous take. Test data only.

---

## The ten checks

| # | Check | Where it happens | What you'll see |
|---|---|---|---|
| 1 | Account creation / login on staging | `login_v1.html` | New account created against staging Supabase Auth, then signed in. Session persists across pages. |
| 2 | Draft profile creation / update | `upload_documents_v1.html` | Profile saved with `verification_status = draft`. Re-saving with a changed field updates the same row — it does not create a second one. |
| 3 | Credential entry | same page | Credential type (degree / license / certification), issuing body, dates. Stored as a `credential_record` row linked to the profile. |
| 4 | Dummy PDF upload to private storage | same page | PDF goes to the **private** `credentials_docs` bucket under `{profile_id}/…`. The stored path is written to `credential_record.documentation_url`. Evidence documents go to `evidence_docs` the same way. 10 MB cap enforced client-side. |
| 5 | Three or more experience records | same page | Three `experience_evidence` rows across categories. The counter pill on screen goes from `experience ≥3: 1` (amber) to green at 3. |
| 6 | Submit-for-review working | same page | The submit button is disabled until the gate passes. The gate is the database function `can_submit_for_review(profile_id)` — not a frontend check — and requires ≥1 identity credential, ≥3 experience records, ≥1 stored document path. Submitting calls `submit_profile_for_review(profile_id)`. |
| 7 | Status changes to `pending_review` | same page, then Supabase | On-screen confirmation, then the same value read back from the database. |
| 8 | Where the rows and the object live in Supabase | Supabase dashboard | Table Editor → `biologist_profile`, `credential_record`, `experience_evidence`. Storage → `credentials_docs` and `evidence_docs`, both marked Private. |
| 9 | The PDF is private and not publicly exposed | private browser window | The object's public URL is opened with no session. It is refused. Then the same object is opened as the owner and it loads. Same file, two results — that is storage RLS doing its job, not a hidden folder. |
| 10 | What is still Milestone 3 | — | Stated explicitly on camera, see below. |

---

## Explicitly still Milestone 3 — not claimed here

- Reviewer queue (the admin-side list of submitted profiles)
- Signed-URL downloads for reviewers
- Approve / reject / partial decisions
- Audit log of those decisions
- Public profile refresh after approval

M2 ends at `pending_review`. Nothing in this package reviews, approves, or
publishes anything, and the Loom says so out loud.

---

## What "working" means here, and what it doesn't

Worth being precise, since the point of this package is that you shouldn't have
to take my word for it.

**Demonstrated:** a real authenticated user, going through the real browser
pages, writing to the real staging database and the real private buckets, with
the submit gate enforced in the database rather than in the page.

**Not demonstrated:** load, concurrency, hostile input, or production hardening.
This is staging with test data, on the free tier, and it should keep being
described that way externally. Production hardening is tracked separately in
`docs/production_migration_checklist_v1.md`.

**Known rough edges, listed so they aren't discovered later:**

- Staging Auth may require email confirmation on new signups. For test accounts
  this is confirmed manually in the Supabase dashboard.
- The staging project is on the free tier and pauses after a stretch of
  inactivity. If a link is dead, it needs restoring first — it isn't a fault in
  the intake path.
- File type is checked by extension, not by inspecting contents. Fine for
  staging, on the M3 hardening list.

---

## Reference

- Technical smoke run, API level: `docs/m2_intake_smoke_v1.md`
- Storage buckets and policies: `database/storage_policies.sql`
- Code: `frontend/login_v1.html`, `frontend/js/biocred_auth.js`,
  `frontend/upload_documents_v1.html`
