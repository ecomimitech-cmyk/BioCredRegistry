# BioCred Registry — Data Model Documentation

## Overview

Three core tables and one audit table. Designed to store biological credentials
in a neutral, structured, and verifiable way.

**No scoring, no ranking, no weighting — descriptive only.**

## Entity Relationship

```
biologist_profile (1) ──── (N) credential_record
        │
        └──────────────── (N) experience_evidence
        │
        └──────────────── (N) verification_audit_log
```

## Table A: biologist_profile

One record per biologist.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Auto-generated unique identifier |
| registry_id | TEXT (unique) | Public-facing ID (e.g., "FC8207") |
| full_name | TEXT | Full legal name |
| professional_title | TEXT | Current title(s) |
| organization | TEXT | Affiliation (optional) |
| state | TEXT | US state |
| city | TEXT | City |
| geographic_region | ENUM | NE, SE, MW, SW, W, NW, Pacific, National |
| years_experience | INTEGER | Total years of professional experience |
| primary_discipline | TEXT | Primary area of expertise |
| taxonomic_focus | ENUM | Primary taxonomic group |
| bio_summary | TEXT | Short professional biography |
| visibility_status | ENUM | draft / active / hidden / suspended |
| verification_status | ENUM | submitted → verified / partial / rejected |
| profile_photo_url | TEXT | URL to profile photo |
| created_at | TIMESTAMPTZ | Record creation timestamp |
| updated_at | TIMESTAMPTZ | Last modification (auto-trigger) |

## Table B: credential_record

Each credential as a separate, linked record. Enables granular verification.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Auto-generated |
| profile_id | UUID (FK) | Links to biologist_profile |
| credential_type | ENUM | degree / certification / license / permit / training / publication / award / other |
| title | TEXT | Credential title (e.g., "M.S. Wildlife Biology") |
| issuing_authority | TEXT | Institution or authority |
| year_issued | INTEGER | Year credential was issued |
| expiration_date | DATE | Expiration (if applicable) |
| documentation_url | TEXT | Link to supporting document |
| verification_status | ENUM | Independent verification per credential |
| verification_method | ENUM | document_review / phone / email / issuer / other |
| verified_by | TEXT | Name of verifier |
| verification_date | DATE | When verification occurred |
| audit_notes | TEXT | Internal notes |
| created_at | TIMESTAMPTZ | Record creation timestamp |

## Table C: experience_evidence

Each entry maps to exactly one of the 5 domains.
This table will later feed the Ionic Domain Model visualization.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Auto-generated |
| profile_id | UUID (FK) | Links to biologist_profile |
| domain_category | ENUM | One of the 5 locked domains |
| activity_type | TEXT | Specific activity performed |
| species_or_system | TEXT | Species or ecological system involved |
| habitat_context | TEXT | Habitat or environmental context |
| project_type | TEXT | Type of project |
| years_applied | INTEGER | Duration of this specific experience |
| role_level | ENUM | participant / contributor / lead / oversight / PI |
| evidence_source | TEXT | Documentation reference |
| is_verified | BOOLEAN | Whether this evidence has been verified |
| created_at | TIMESTAMPTZ | Record creation timestamp |

## Table D: verification_audit_log

Immutable log of all status changes for accountability.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (PK) | Auto-generated |
| profile_id | UUID (FK) | Links to biologist_profile |
| credential_id | UUID (FK, nullable) | Specific credential if applicable |
| previous_status | ENUM | Status before change |
| new_status | ENUM | Status after change |
| changed_by | TEXT | Who made the change |
| change_reason | TEXT | Why the change was made |
| created_at | TIMESTAMPTZ | When the change occurred |

## Domain Categories (Locked)

| ENUM Value | Display Name | Color Ref |
|------------|-------------|-----------|
| field_experience | Field Experience | Green |
| regulatory_experience | Regulatory Experience | Blue |
| academic_technical | Academic / Technical | Purple |
| species_depth | Species Depth | Cyan/Teal |
| leadership_scope | Leadership / Responsibility Scope | Gray |

## Key Design Decisions

1. **UUIDs as primary keys** — portable, no sequential exposure
2. **Registry IDs are separate** — public-facing, human-readable
3. **Per-credential verification** — granular trust, not all-or-nothing
4. **Audit log is append-only** — full traceability
5. **ENUMs for categories** — prevents inconsistent data entry
6. **No computed fields** — no scores or weighted values stored
7. **Cascading deletes** — removing a profile cleans linked records
