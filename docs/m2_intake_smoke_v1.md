# BioCred M2 — Evidence Intake Smoke (staging)

**Project:** `biocred-staging` · `https://wmwzqnzyhiyhfzncuxkc.supabase.co`  
**Last run:** 2026-08-11  
**Scope:** Auth → draft profile → private upload → credentials/experience → `pending_review`  
**Out of scope:** reviewer queue, signed URLs, approve/reject (M3)

## Prerequisites

1. Buckets + policies applied: `database/storage_policies.sql`
2. Frontend config: copy `frontend/config.example.js` → `frontend/config.js` (see also `.env.example`)
3. Serve `frontend/` over HTTP (or open via a local static server) so modules load

## Manual click-through

1. Open `frontend/login_v1.html` → create account (or sign in).
   - Staging may require email confirmation. For test users, confirm in Supabase Auth dashboard, or set `auth.users.email_confirmed_at = now()` for that email.
2. Open `frontend/upload_documents_v1.html`.
3. Save a draft profile (accept terms on first create).
4. Upload a degree/license/certification PDF (private `credentials_docs`).
5. Add ≥3 experience records (form on the same page).
6. When pills show “ready to submit”, click **Submit profile for review**.
7. Confirm profile `verification_status = pending_review`.

## Automated API smoke (2026-08-11) — PASS

| Check | Result |
|---|---|
| Biologist Auth session | PASS |
| `ensure_biologist_role` | PASS |
| Insert draft `biologist_profile` linked to `auth_user_id` | PASS |
| Upload PDF to `credentials_docs` under `{profile_id}/…` | PASS (HTTP 200) |
| Insert `credential_record` with `documentation_url` path | PASS |
| Insert ≥3 `experience_evidence` | PASS |
| `can_submit_for_review(profile_id)` → true | PASS |
| `submit_profile_for_review(profile_id)` → profile + rows `pending_review` | PASS |
| Anon GET object | denied (HTTP 400) |
| Owner GET object | PASS (HTTP 200) |

Example smoke profile: `registry_id = SM7523` (staging test data; safe to delete later).

## Files touched for M2

- `database/storage_policies.sql` — buckets, storage RLS, role bootstrap, submit RPC
- `frontend/login_v1.html` — signup / sign-in
- `frontend/js/biocred_auth.js` — shared client + profile helpers
- `frontend/upload_documents_v1.html` — wired intake (no mock alert)
- `frontend/config.example.js`, `.env.example`

## Acceptance (vesting M2)

A real authenticated test user can create a profile, add ≥1 identity credential with a private PDF, add ≥3 experience records, and submit to `pending_review` without mock alerts.
