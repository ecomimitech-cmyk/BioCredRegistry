# BioCred Registry — Architecture

## System Overview

BioCred Registry is a neutral credential documentation platform for biological professionals.
The architecture prioritizes data integrity, verification traceability, and neutral presentation.

## Phase 1 Architecture: Data Foundation

### Database Layer

**Engine**: PostgreSQL (Supabase-compatible)

Three core tables with relational links:

```
┌─────────────────────┐
│   biologist_profile  │  ← One per person
│─────────────────────│
│ id (PK)             │
│ registry_id         │
│ full_name           │
│ professional_title  │
│ organization        │
│ region / state      │
│ years_experience    │
│ primary_discipline  │
│ bio_summary         │
│ visibility_status   │
│ verification_status │
│ created_at          │
│ updated_at          │
└────────┬────────────┘
         │ 1:N
         ▼
┌─────────────────────┐     ┌─────────────────────┐
│  credential_record   │     │  experience_evidence  │
│─────────────────────│     │─────────────────────│
│ id (PK)             │     │ id (PK)             │
│ profile_id (FK)     │     │ profile_id (FK)     │
│ credential_type     │     │ domain_category     │
│ issuing_authority   │     │ activity_type       │
│ year_issued         │     │ species_or_system   │
│ expiration_date     │     │ habitat_context     │
│ documentation_url   │     │ project_type        │
│ verification_status │     │ years_applied       │
│ verification_method │     │ role_level          │
│ verified_by         │     │ evidence_source     │
│ audit_notes         │     │ is_verified         │
│ created_at          │     │ created_at          │
└─────────────────────┘     └─────────────────────┘
```

### Domain Categories (Locked for Phase 1)

1. Field Experience
2. Regulatory Experience
3. Academic / Technical
4. Species Depth
5. Leadership / Responsibility Scope

These are structured as an ENUM type in PostgreSQL — no weighting, no scoring.

### Verification States

```
submitted → pending_review → under_verification → verified | rejected | partial
```

Each state transition is logged in `verification_audit_log` for traceability.

### Future: Ionic Domain Model Integration

The `experience_evidence` table feeds the future visualization system.
Each record maps to one of the 5 domains, and aggregated data will produce
the "centroid vector" for the BioCred Experience Profile — but **no math or visualization
is implemented in Phase 1**.

## Key Constraints

- No composite scores calculated anywhere in the system
- No domain weighting applied
- Verification = documentation review, not endorsement
- All status changes are auditable
- Profile visibility is controlled by the biologist

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Database | PostgreSQL/Supabase | Relational integrity, easy API, scalable |
| Schema | SQL migrations | Reproducible, version-controlled |
| Seed data | SQL inserts | Testable, portable |
| Future CMS | Webflow | Client requirement for Phase 2+ |
| Future viz | Custom (Ionic Domain Model) | Proprietary design, Phase 2+ |
