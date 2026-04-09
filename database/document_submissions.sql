-- BioCred Registry — Document Submission Schema
-- PostgreSQL / Supabase-ready
-- Phase A: Biologist document upload flow
-- Categories per Alexander Funk spec (Apr 2026)

-- ============================================================
-- ENUM: document categories
-- ============================================================

CREATE TYPE document_category AS ENUM (
    'resume',
    'transcript',
    'certification',
    'continuing_education',
    'degree',
    'reference_letter',
    'award',
    'license',
    'permit',
    'other'
);

CREATE TYPE document_status AS ENUM (
    'draft',
    'submitted',
    'under_review',
    'approved',
    'rejected',
    'requires_resubmission'
);

-- ============================================================
-- TABLE: document_submissions
-- One row per document uploaded by a biologist
-- ============================================================

CREATE TABLE document_submissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES biologist_profiles(id) ON DELETE CASCADE,

    -- Core classification
    category            document_category NOT NULL,
    document_title      TEXT NOT NULL,                -- e.g. "B.S. Wildlife Biology, UC Davis"
    issuing_authority   TEXT,                         -- e.g. "UC Davis", "CDFW", "Cornell"
    issue_date          DATE,
    expiry_date         DATE,                         -- for licenses, permits, certs

    -- CE credit fields (only for category = 'continuing_education')
    ce_provider         TEXT,                         -- e.g. "Cornell Online", "TWS", "NWTI"
    ce_subject          TEXT,                         -- e.g. "GIS for Wildlife", "NEPA Compliance"
    ce_hours            NUMERIC(5,1),                 -- e.g. 12.5
    ce_completion_date  DATE,

    -- Reference fields (only for category = 'reference_letter')
    reference_name      TEXT,
    reference_title     TEXT,
    reference_org       TEXT,
    reference_email     TEXT,

    -- Permit / license fields
    permit_type         TEXT,                         -- e.g. "Section 10(a)(1)(A) ESA", "MOU"
    permit_number       TEXT,
    jurisdiction        TEXT,                         -- e.g. "California", "Federal"

    -- File storage
    file_path           TEXT,                         -- Supabase Storage path (private bucket)
    file_name           TEXT,
    file_size_bytes     BIGINT,
    mime_type           TEXT,

    -- Review state
    status              document_status NOT NULL DEFAULT 'draft',
    reviewer_notes      TEXT,
    reviewed_by         UUID REFERENCES auth.users(id),
    reviewed_at         TIMESTAMPTZ,

    -- Certification: biologist attests all info is true and correct
    biologist_certified     BOOLEAN NOT NULL DEFAULT FALSE,
    biologist_certified_at  TIMESTAMPTZ,

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups by profile
CREATE INDEX idx_doc_submissions_profile ON document_submissions(profile_id);
CREATE INDEX idx_doc_submissions_status  ON document_submissions(status);
CREATE INDEX idx_doc_submissions_category ON document_submissions(category);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_doc_submissions_updated
BEFORE UPDATE ON document_submissions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- RLS POLICIES
-- ============================================================

ALTER TABLE document_submissions ENABLE ROW LEVEL SECURITY;

-- Biologists can only see and manage their own submissions
CREATE POLICY "biologist_own_docs" ON document_submissions
    FOR ALL
    USING (
        profile_id IN (
            SELECT id FROM biologist_profiles WHERE user_id = auth.uid()
        )
    );

-- Reviewers can read all submitted (not draft) documents
CREATE POLICY "reviewer_read_submitted" ON document_submissions
    FOR SELECT
    USING (
        status != 'draft'
        AND EXISTS (
            SELECT 1 FROM auth.users
            WHERE id = auth.uid()
            AND raw_user_meta_data->>'role' IN ('reviewer', 'admin')
        )
    );

-- Reviewers can update status and add notes
CREATE POLICY "reviewer_update_status" ON document_submissions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM auth.users
            WHERE id = auth.uid()
            AND raw_user_meta_data->>'role' IN ('reviewer', 'admin')
        )
    )
    WITH CHECK (TRUE);
