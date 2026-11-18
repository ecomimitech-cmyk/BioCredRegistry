# M5 closeout — working log

Running record of the checks made to close Milestone 5. Newest at the bottom.
Staging project: `wmwzqnzyhiyhfzncuxkc` · demo: https://biocred-staging-demo.netlify.app

---

## 18 Nov 2026 — Group 1 changes (Alex's 15 Oct note)

Checked in code (`frontend/`, `renderer/`) and confirmed `deploy/` is byte-identical
to source (hash comparison of all 18 deployed files), so what is in code is what is live.

| Change | Where | State |
|---|---|---|
| "Experience Summary" + "Derived from verified documentation" | `public_profile_v1.html:177` | done |
| No "sparse"/"limited"; "Documented experience concentrated in…" | `js/public_profile_page.js:128` | done |
| No Specialist/Expert titles | grep: none in frontend | done |
| Directory A–Z until search/filter, then relevance | `js/directory_page.js:36` | done |
| "Applicant Attestation" | `upload_documents_v1.html:224` | done |
| Sign in / Create account as tabs | `login_v1.html:18-46` | done |
| Centroid line only when explicitly enabled | `renderer/biocred-renderer.js:368` (`centroidLine === true`) | done |
| Stronger green density scale | `renderer/biocred-renderer.js:67` | done |

## 18 Nov 2026 — anonymous security probe

Script: copy of `qa/anon_probe_v1.ps1` with `PEND99` → `PEND01`
(PEND99 was marked partial on 14 Oct and is now public by design; PEND01 is the
pending refuse-check created by `database/m5_pend01_refuse_check_v1.sql`).

Result: **22 / 22 passed.**

- All five base tables (`biologist_profile`, `credential_record`, `experience_evidence`,
  `verification_audit_log`, `user_roles`) return `permission denied` to anon
  → `m5_anon_base_table_lockdown_v1.sql` **is applied**.
- `render_payload_cache` denied to anon.
- Public view returns 7 profiles: FC2401–FC2405, SM7523 (verified), PEND99 (partial). PEND01 absent.
- Storage: no object without signed URL; bucket listing empty.

Probe weaknesses noticed (not system defects):
- The `evidence_public_v1` / `credential_public_v1` probes "pass" only because those views
  have no `registry_id` column (400). They key on `profile_id`. Should be rewritten to filter
  by PEND01's profile id.
- The script's verdict for `submit_profile_for_review` passes on any non-200. Body check added by hand:

```
POST rpc/submit_profile_for_review {p_profile_id, p_note}  → P0001 not_profile_owner
POST rpc/submit_profile_for_review {p_profile_id}          → P0001 not_profile_owner
```

The two-argument signature resolves, so **`m5_resubmission_v1.sql` is applied**.
Side note: `anon` can *execute* the function (Supabase grants EXECUTE to anon by default;
`REVOKE … FROM PUBLIC` does not remove it). Harmless — the owner check refuses — but a
`REVOKE EXECUTE … FROM anon` is good hygiene for production.

## 18 Nov 2026 — resubmission end to end

Reviewer signed in on staging (reviewer test account). Queue state after refresh:
pending 0 · under review 0 · verified 6 · partial 1 · rejected 0 · total 7.

Finding: there is **no pending submission** to reject, and the biologist test account's
only profile (SM7523) is verified — which the new rule correctly refuses to resubmit.
To exercise the path, a pending profile owned by a biologist account is needed first.

Approach chosen: rather than create throwaway accounts and upload files through the UI,
the loop runs as one SQL transaction that is **rolled back** at the end —
`database/m5_resubmission_e2e_test_v1.sql`. It switches between the real roles
(reviewer, biologist, anon) with their real permissions, so it exercises the same
functions and policies the pages call, and leaves staging, the audit log and the
public page exactly as they were. Eight steps, each prints a NOTICE; any failure aborts.

Run in the Supabase SQL Editor (biocred-staging), Owner session.

First run: steps 1–3 passed, **step 4 failed — a defect in the test, not the system.**
Every row written in one transaction shares the same `created_at` (`now()` is the
transaction start), so "latest audit row" picked the setup row instead of the
resubmission row. Fixed by selecting the row by content. The failure aborted the
transaction, so nothing was written.

Second run — output, verbatim:

```
M5 RESUBMISSION E2E
setup     SM7523 -> pending_review
step 1    reviewer rejected with a reason -> rejected
step 2    anon cannot see rejected SM7523
step 3    resubmission without a note refused: resubmission_note_required
step 4    resubmitted with a note -> pending_review, audit: "resubmitted after rejection: Replaced the licence scan with a legible copy."
step 5    prior rejection on record (1 row/s): queue shows "resubmitted"
step 6    reviewer approved -> verified
step 7    anon sees SM7523 again
step 8    verified profile cannot be resubmitted: not_submittable_from_verified
ALL 8 STEPS PASSED.
```

(The script deliberately ends by raising this log as an error: the editor shows it,
and the error forces the rollback.)

Rollback confirmed from outside: `profile_public_v1` still returns SM7523 as
`verified` with `updated_at` 2026-10-13 — unchanged.

Note: the editor kept the query as an unsaved "Untitled query" tab in the dashboard.

Result written into `BioCred_M5_Closeout_Package_v1.html` §6.

## Still open before sending the package

- Push current code, the M5 database scripts, this test and the QA scripts to the
  shared GitHub repository; then mark Exhibit A row G "met" in the package.
- Publish the package next to the other documents on the demo site and put the link
  in `mensaje-para-alex-m5-cierre.txt`.
