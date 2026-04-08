# BioCred Registry — Verification Workflow

## Guiding Principle

**"Trust but Verify"**

Verification confirms that documentation exists and is authentic.
It does **not** evaluate quality, competence, or professional merit.

---

## Status Labels

| Status | Meaning |
|--------|---------|
| `submitted` | Profile created, no review initiated |
| `pending_review` | Queued for admin review |
| `under_verification` | Active verification in progress |
| `verified` | All submitted credentials confirmed |
| `partial` | Some credentials verified, others pending |
| `rejected` | Documentation could not be confirmed |

---

## Workflow Diagram

```
┌──────────────────┐
│  Biologist signs  │
│  up & submits     │
│  profile          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Credentials      │
│  uploaded          │
│  Status: SUBMITTED │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Admin receives   │
│  notification     │
│  Status: PENDING  │
│  REVIEW           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Admin reviews    │
│  documentation    │
│  Status: UNDER    │
│  VERIFICATION     │
└────────┬─────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
┌──────────┐     ┌──────────────┐
│ Documents │     │ Documents     │
│ sufficient│     │ insufficient  │
└─────┬────┘     └──────┬───────┘
      │                  │
      │                  ▼
      │          ┌──────────────┐
      │          │ Phone / email │
      │          │ verification  │
      │          └──────┬───────┘
      │                  │
      │         ┌────────┼────────┐
      │         │        │        │
      ▼         ▼        ▼        ▼
┌─────────┐ ┌───────┐ ┌───────┐ ┌────────┐
│VERIFIED │ │VERIFIED│ │PARTIAL│ │REJECTED│
└─────────┘ └───────┘ └───────┘ └────────┘
                  │
                  ▼
         ┌──────────────┐
         │ Audit log     │
         │ entry created │
         │ (immutable)   │
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Public        │
         │ registry      │
         │ display       │
         │ (if active)   │
         └──────────────┘
```

---

## Verification Checklist

### Document Review
- [ ] Profile information is complete and consistent
- [ ] Credential documents are legible and unexpired
- [ ] Issuing authority is identifiable
- [ ] Degree(s) match stated education
- [ ] Professional title is consistent with credentials

### Phone / Email Confirmation (if needed)
- [ ] Contact info for issuing authority obtained
- [ ] Confirmation request sent or call placed
- [ ] Response received and documented
- [ ] Outcome recorded in audit log

### Final Decision
- [ ] All credentials reviewed individually
- [ ] Status assigned per credential
- [ ] Overall profile status determined
- [ ] Audit log entry created with reason
- [ ] Biologist notified of outcome

---

## Who Can Change Status

| Action | Authorized By |
|--------|---------------|
| Submit profile | Biologist (self-service) |
| Move to pending_review | System (automatic) |
| Move to under_verification | Admin reviewer |
| Set verified / partial / rejected | Admin reviewer |
| Override status | Platform administrator only |
| View audit log | Admin reviewer, platform admin |

---

## Audit Trail Requirements

Every status change **must** record:

1. **Who** changed the status (`changed_by`)
2. **When** the change occurred (`created_at`)
3. **From** what status (`previous_status`)
4. **To** what status (`new_status`)
5. **Why** the change was made (`change_reason`)
6. **Which credential** if applicable (`credential_id`)

Audit log entries are **append-only** — cannot be edited or deleted.

---

## Required Evidence Levels

| Credential Type | Minimum Evidence |
|----------------|-----------------|
| Degree | Diploma scan, transcript, or university confirmation |
| Certification | Certificate document or issuing body confirmation |
| License | License document with number and expiration |
| Permit | Permit document with authorization details |
| Training | Certificate of completion or training record |
| Publication | DOI, journal reference, or document copy |
| Field experience | Project documentation or employer confirmation |

---

## Important Constraints

- Verification does **not** imply endorsement
- "Verified" means "documentation reviewed and confirmed"
- No quality judgment is made at any stage
- Partial verification is acceptable and clearly labeled
- Rejected status must include specific reason
- Biologists may resubmit with additional documentation
