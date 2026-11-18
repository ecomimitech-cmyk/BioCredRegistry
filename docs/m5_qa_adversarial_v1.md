# M5 QA — adversarial pass on the anonymous surface

**Run:** 18 Sep 2026, staging (`wmwzqnzyhiyhfzncuxkc`)
**Script:** `qa/anon_probe_v1.ps1`, follow-ups in `qa/anon_leak_detail_v1.ps1` and `qa/anon_columns_v1.ps1`
**Position assumed:** a stranger holding nothing but the publishable key printed in the page source.

22 probes. 18 passed outright, 3 were my expectation being wrong rather than the
system being wrong, and 1 was a real defect.

## Held

- **Writing anywhere.** Inserts into `biologist_profile`, `user_roles` and
  `verification_audit_log` were all refused at the grant level, before RLS was
  even consulted. Self-promotion to admin is not reachable from the browser.
- **The audit trail.** `verification_audit_log` and `user_roles` refuse
  anonymous reads outright — `permission denied for table`.
- **The privileged functions.** `grant_role_by_email`, `review_start`,
  `review_decide` and `submit_profile_for_review` all refused an anonymous
  caller. `is_reviewer_or_admin` returned false rather than erroring, which is
  the right shape of answer.
- **Unapproved profiles.** PEND99 is absent from `profile_public_v1`,
  `profile_render_v1`, `evidence_public_v1` and `credential_public_v1`, and
  stays absent when the status filter is removed and the row limit raised.
  SM7523, which was approved, is present. The gate is the approval, not the URL.
- **Documents.** Storage refused every unsigned request, and listing the
  `evidence_docs` bucket returned nothing. Holding a document's path does not
  get you the document.
- **Injected markup.** Every field a biologist controls — name, title,
  organisation, credential titles, species — is escaped before it reaches the
  page, on both the new directory and the public profile. Nothing a user types
  can execute for the next visitor.

## Expectation was wrong, not the system

`biologist_profile` (6 rows), `credential_record` (22) and `experience_evidence`
(53) are readable anonymously. I had expected silence. Checking what actually
comes back: every row is `verified`, and **zero** belong to a profile that is not
already publicly listed. RLS is filtering correctly. `render_payload_cache` is
the same — 6 cached payloads, all for public profiles.

## Defect found, fix written

**Anonymous reads of `credential_record` include `documentation_url`.**

That column is the storage path of every uploaded document:

```
b2413861-…/f10862fd-…/2026-08-11_smoke-degree.pdf
```

The file stays shut — storage refused every unsigned request in the same run.
But the path carries the owner's auth user id and the original filename. On
staging those filenames are invented. On a real registry they read
`jane-smith-phd-diploma.pdf`, and that is a person's name and qualification
handed to anyone who reads the page source.

`credential_public_v1` deliberately omits this column. Reading the base table
walked around the view that was protecting it.

**Fix:** `database/m5_anon_base_table_lockdown_v1.sql` revokes the anonymous
read on all four base tables. Nothing anonymous needs them — every public page
reads the `_public_v1` views; only the reviewer portal and the intake form touch
base tables, and both run signed in, so `authenticated` keeps its grant.

The migration verifies itself: inside the same transaction it takes on the `anon`
role, re-reads the four public views, and raises if any came back empty — which
rolls the revoke back and leaves staging untouched. It is safe to run blind.

## Not yet covered

The resubmission path (`database/m5_resubmission_v1.sql`) has not been exercised
against staging, because applying it needs the SQL Editor. Once it is applied,
the run to make is: reject SM7523 with a reason, confirm it drops off the public
directory, correct it, confirm the send-back is refused with no note, resubmit
with one, and confirm the reviewer sees the `resubmitted` tag and both sides of
the exchange in the decision trail.
