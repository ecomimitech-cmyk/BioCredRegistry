# BioCred Onboarding Workflow v1.0

**Source:** Alexander Funk, March 2 2026

---

## Overview

This document specifies the BioCred onboarding workflow for biologists joining the registry. The flow guides users from account creation through profile submission and verification.

---

## Roles

| Role | Description |
|------|-------------|
| **Public** | Read-only access to published profiles |
| **Biologist** | Profile owner; creates and manages their own profile |
| **Reviewer** | Verifies evidence and credentials |
| **Admin** | Manages verification queue and system configuration |

---

## Step 1: Create Account

- **Email + password** or **magic link** authentication
- User must **accept terms** before proceeding
- Standard account creation flow

---

## Step 2: Create Draft Profile

- **5-minute form** collecting:
  - Name
  - Title
  - Organization
  - Location
  - Summary
  - Visibility preference

- **Supabase write:** `biologist_profile` with:
  - `verification_status = submitted`
  - `visibility_status = private`

---

## Step 3: Add Evidence

Evidence is collected in two buckets:

### A) Credentials

- Degree
- Certification
- License
- Permit
- Training
- Publication
- **Document upload** required for each credential

### B) Experience Evidence

- `domain_category`
- `activity_type`
- `species`
- `habitat`
- `project_type`
- `role_level`
- `time_range`
- `evidence_source`

---

## Step 4: Submit for Review

- **Submit button** unlocks when all of the following are met:
  - ≥ 1 identity credential
  - ≥ 3 experience records
  - ≥ 1 document upload

- User clicks **Submit for Review** to enter the verification queue

---

## Tiered Verification

| Tier | Scope | Typical Duration |
|------|-------|------------------|
| **Tier 1** | Quick check | 5–10 minutes |
| | Identity anchor + high-risk items | |
| **Tier 2** | Progressive deeper checks | Ongoing |

---

## Public Display Rules

- Only **verified** or **partial** profiles with **public visibility** are shown
- Only show evidence items where `status != rejected`
- Rejected items are never displayed publicly

---

## Supabase Design

### Storage Buckets

| Bucket | Purpose |
|--------|---------|
| `credentials_docs` | Credential documentation uploads |
| `evidence_docs` | Experience evidence supporting documents |

### Security

- **RLS policies** per table
- **Append-only audit log** for verification actions

---

## Admin Minimization

- **Verification queue view** for reviewers
- **Auto-flags** for:
  - Species handling
  - Permits
  - Lead/PI claims
- **Verification templates** to standardize common checks

---

## UX Requirements

- **Save-and-resume:** Users can leave and return without losing progress
- **Progress indicator:** Clear indication of completion state
- **Optional CV importer:** Ability to import from CV/PDF (Phase 1 optional)

---

## Pilot Plan

- **Invite-only** for first 25 profiles
- **72-hour verification SLA** for pilot participants

---

## Summary Checklist

- [ ] Account creation (email/password or magic link)
- [ ] Terms acceptance
- [ ] Draft profile (5-min form)
- [ ] Credentials bucket (≥1 identity credential + doc upload)
- [ ] Experience evidence bucket (≥3 records)
- [ ] Submit for review (unlock criteria met)
- [ ] Tier 1 + Tier 2 verification
- [ ] Public display rules enforced
- [ ] Supabase buckets + RLS + audit log
- [ ] Admin tools (queue, auto-flags, templates)
- [ ] Save-and-resume + progress indicator
- [ ] Pilot: 25 profiles, 72-hour SLA
