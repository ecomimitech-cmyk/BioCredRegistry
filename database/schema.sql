-- BioCred Registry — Core Database Schema
-- PostgreSQL / Supabase-ready
-- Phase 1: Foundational Data Model
-- Descriptive only — no evaluative metrics

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE verification_status AS ENUM (
    'submitted',
    'pending_review',
    'under_verification',
    'verified',
    'partial',
    'rejected'
);

CREATE TYPE domain_category AS ENUM (
    'field_experience',
    'regulatory_experience',
    'academic_technical',
    'species_depth',
    'leadership_scope'
);

CREATE TYPE credential_type AS ENUM (
    'degree',
    'certification',
    'license',
    'permit',
    'training',
    'publication',
    'award',
    'other'
);

CREATE TYPE verification_method AS ENUM (
    'document_review',
    'phone_confirmation',
    'email_confirmation',
    'issuer_verification',
    'other'
);

CREATE TYPE role_level AS ENUM (
    'participant',
    'contributor',
    'lead',
    'oversight',
    'principal_investigator'
);

CREATE TYPE visibility_status AS ENUM (
    'draft',
    'active',
    'hidden',
    'suspended'
);

CREATE TYPE geographic_region AS ENUM (
    'northeast',
    'southeast',
    'midwest',
    'southwest',
    'west',
    'northwest',
    'pacific',
    'national'
);

CREATE TYPE taxonomic_group AS ENUM (
    'avian',
    'mammal',
    'fish',
    'reptile',
    'amphibian',
    'botany',
    'invertebrate',
    'multi_taxa'
);

-- ============================================================
-- TABLE A: BIOLOGIST PROFILES
-- ============================================================

CREATE TABLE biologist_profile (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registry_id         TEXT UNIQUE NOT NULL,
    full_name           TEXT NOT NULL,
    professional_title  TEXT,
    organization        TEXT,
    state               TEXT,
    city                TEXT,
    geographic_region   geographic_region,
    years_experience    INTEGER CHECK (years_experience >= 0),
    primary_discipline  TEXT,
    taxonomic_focus     taxonomic_group,
    bio_summary         TEXT,
    visibility_status   visibility_status DEFAULT 'draft',
    verification_status verification_status DEFAULT 'submitted',
    profile_photo_url   TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_profile_region ON biologist_profile(geographic_region);
CREATE INDEX idx_profile_state ON biologist_profile(state);
CREATE INDEX idx_profile_verification ON biologist_profile(verification_status);
CREATE INDEX idx_profile_visibility ON biologist_profile(visibility_status);
CREATE INDEX idx_profile_discipline ON biologist_profile(primary_discipline);

-- ============================================================
-- TABLE B: CREDENTIAL RECORDS
-- ============================================================

CREATE TABLE credential_record (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES biologist_profile(id)
                        ON DELETE CASCADE,
    credential_type     credential_type NOT NULL,
    title               TEXT NOT NULL,
    issuing_authority   TEXT,
    year_issued         INTEGER,
    expiration_date     DATE,
    documentation_url   TEXT,
    verification_status verification_status DEFAULT 'submitted',
    verification_method verification_method,
    verified_by         TEXT,
    verification_date   DATE,
    audit_notes         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_credential_profile ON credential_record(profile_id);
CREATE INDEX idx_credential_type ON credential_record(credential_type);
CREATE INDEX idx_credential_verification
    ON credential_record(verification_status);

-- ============================================================
-- TABLE C: EXPERIENCE EVIDENCE
-- ============================================================

CREATE TABLE experience_evidence (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES biologist_profile(id)
                        ON DELETE CASCADE,
    domain_category     domain_category NOT NULL,
    activity_type       TEXT NOT NULL,
    species_or_system   TEXT,
    habitat_context     TEXT,
    project_type        TEXT,
    years_applied       INTEGER CHECK (years_applied >= 0),
    role_level          role_level DEFAULT 'participant',
    evidence_source     TEXT,
    is_verified         BOOLEAN DEFAULT FALSE,
    translation_version TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_evidence_profile ON experience_evidence(profile_id);
CREATE INDEX idx_evidence_domain ON experience_evidence(domain_category);
CREATE INDEX idx_evidence_verified ON experience_evidence(is_verified);

-- ============================================================
-- VERIFICATION AUDIT LOG
-- ============================================================

CREATE TABLE verification_audit_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES biologist_profile(id)
                        ON DELETE CASCADE,
    credential_id       UUID REFERENCES credential_record(id)
                        ON DELETE SET NULL,
    previous_status     verification_status,
    new_status          verification_status NOT NULL,
    changed_by          TEXT NOT NULL,
    change_reason       TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_profile ON verification_audit_log(profile_id);
CREATE INDEX idx_audit_date ON verification_audit_log(created_at);

-- ============================================================
-- AUTO-UPDATE TIMESTAMP TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_profile_updated_at
    BEFORE UPDATE ON biologist_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
