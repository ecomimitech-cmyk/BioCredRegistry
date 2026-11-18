# BioCred M3 — Reviewer decision layer (runbook + smoke)

**Project:** `biocred-staging` · `https://wmwzqnzyhiyhfzncuxkc.supabase.co`
**Status:** built, **not yet applied to staging** — see step 1
**Scope:** reviewer queue → signed-URL document access → verify / partial / reject → audit trail
**Out of scope:** public profile refresh and the experience map (M4)

---

## What was added

| Piece | File |
|---|---|
| `review_start()`, `review_decide()`, audit-reason plumbing, role bootstrap | `database/review_actions.sql` |
| Reviewer portal, wired | `frontend/agency_review_v1.html` |

The page was a static prototype with hardcoded rows. It now reads the real
queue, opens real private documents through signed URLs, and writes real
decisions through database functions.

### The audit fix worth knowing about

The Block 1 trigger already logged every `verification_status` change, but it
recorded the reason as the literal string `auto_trigger`. That tells a future
auditor that something changed and nothing about why, which is most of the value
of an audit log gone.

`review_decide()` now sets a transaction-local setting that the trigger reads, so
the reviewer's stated reason lands on the audit row. Anything that changes a
status *outside* those functions still records `auto_trigger` — which is exactly
the signal you'd want, because it marks a change nobody justified.

---

## 1 · Apply the SQL

Supabase dashboard → SQL Editor → paste the whole of `database/review_actions.sql`
→ Run. It is idempotent; re-running is safe.

## 2 · Create a reviewer account

Reviewer access is granted deliberately and cannot be self-assigned. There is no
path from the browser to becoming a reviewer, by design.

1. Sign up a second account at `login_v1.html`, e.g. `reviewer@…`
   (confirm it in Auth → Users if staging asks for confirmation)
2. In the SQL Editor:

```sql
SELECT grant_role_by_email('reviewer@example.com', 'reviewer');
```

`grant_role_by_email` is granted to nobody — not `anon`, not `authenticated`. It
runs only from the SQL editor or psql as the database owner.

## 3 · Run the path

Open `agency_review_v1.html` signed in as the reviewer.

| # | Check | Expected |
|---|---|---|
| 1 | Signed in as a **biologist**, open the portal | The "not a reviewer" gate. No queue, no data. |
| 2 | Signed in as the **reviewer** | Queue loads, the M2 profile sits in Pending review |
| 3 | Open the submission | Profile fields, credentials, experience records, empty-ish audit trail |
| 4 | Click **Open** on a credential | The PDF opens through a signed URL valid for 5 minutes |
| 5 | Copy that signed URL, wait past expiry, reopen | Refused — the link is short-lived, the bucket is still private |
| 6 | **Start review** | Status → Under review, audit row "Review started" |
| 7 | **Reject** with the reason box empty | Refused: a reason is required |
| 8 | **Verify** | Status → Verified, profile becomes `visibility_status = active`, credentials and experience rows follow |
| 9 | Audit trail | One row per changed record, each carrying the reviewer's real reason and their user id |
| 10 | Try to decide again on the same profile | Refused: already decided |
| 11 | Back as the **biologist** | Own profile shows Verified; no access to anyone else's submission |

## 4 · Results — run 2026-08-27, staging, **19/19 PASS**

Applied to staging via psql on the pooler. Run end to end against the real M2
submission `SM7523` (3 credentials, 8 experience records).

| # | Check | Result |
|---|---|---|
| 1 | Reviewer and biologist sign in | PASS |
| 2 | `is_reviewer_or_admin` true for reviewer, false for biologist | PASS |
| 3 | Queue shows the pending submission | PASS — `SM7523` |
| 4 | Reviewer reads credentials and evidence | PASS — 3 creds, 8 records |
| 5 | Reviewer signs a private document | PASS — `2026-08-11_smoke-degree.pdf` |
| 5b | Signed link opens with no session | PASS |
| 5c | Same object without a signature is refused | PASS |
| 6 | Biologist blocked from deciding | PASS — `not_a_reviewer` |
| 7 | `review_start` → `under_verification` | PASS |
| 8 | Rejection with no reason refused | PASS — `reason_required` |
| 9 | Approval succeeds | PASS |
| 9b | Profile `verified` **and** `visibility_status = active` | PASS |
| 9c | Credentials carried to verified, `verified_by` set | PASS — 3 rows |
| 10 | Audit log written | PASS — 13 rows for this decision |
| 10b | Reviewer's real reason recorded on every row | PASS |
| 10c | No `auto_trigger` on these decisions | PASS — 0 in the window |
| 11 | Deciding twice is refused | PASS — `profile_not_reviewable` |

**One note on check 10c.** The first run reported it as a failure. The check was
wrong, not the code: it read the profile's last 25 audit rows, which reach back
to the M2 submission on 11 Aug — written before the reason plumbing existed, so
they legitimately say `auto_trigger`. Scoped to the decisions actually made in
this run, the count of `auto_trigger` rows is **zero** and all 13 carry the
reviewer's stated reason. Worth keeping in the record because it is exactly the
distinction the audit log is supposed to make: old unexplained changes stay
visible as unexplained rather than being rewritten.

### The M4 gap, now visible with real data

Immediately after approval, `profile_render_v1` still returns only `FC2401` —
the hand-written demo seed. `SM7523` is verified and active and **does not appear
publicly**, because nothing has written a `render_payload_cache` row for it.

That is the whole of M4's data path, demonstrated rather than asserted.
`pipeline/refresh_render_cache.py` is written and self-tested offline; it needs
`SUPABASE_SERVICE_ROLE_KEY` to run against staging.

### Test accounts

Credentials for the reviewer and biologist smoke accounts are in
`.env.smoke` at the repo root, which is git-ignored. They are staging test users
and can be deleted at any time.

---

## Deliberate design notes

**The gate is in the database, not the page.** `review_decide()` refuses a
non-reviewer, refuses a missing reason on a rejection or a partial, and refuses a
submission that has already been decided. Disabling a button is a courtesy to the
user; the function is what actually enforces it.

**Nothing becomes public by accident.** `visibility_status` is set to `active`
only on verify or partial. A rejected profile is never made visible.

**Documents never get a permanent URL.** Reviewers read private objects through
signed links with a five-minute life. The buckets stay private throughout, which
is the same property demonstrated in the M2 package.

**Known gaps, honestly:**

- A rejected profile has no resubmission path yet — the biologist can't
  currently reopen it. That belongs to M3 polish or M5.
- No per-credential decisions; a decision applies to the whole submission.
- `render_payload_cache` is not refreshed on approval, so the public profile
  won't light up yet. That is M4 and is the next piece of work.
