-- BioCred Registry — Supabase RLS Policies & Auth Extensions
-- Per Alexander Funk's Onboarding Workflow v1.0
-- Requires: Supabase Auth enabled, storage buckets created

-- ============================================================
-- SCHEMA EXTENSIONS (auth-aware columns)
-- ============================================================

ALTER TABLE biologist_profile
    ADD COLUMN IF NOT EXISTS auth_user_id UUID REFERENCES auth.users(id),
    ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_auth_user
    ON biologist_profile(auth_user_id);

-- ============================================================
-- CUSTOM TYPES FOR ROLES
-- ============================================================

CREATE TYPE app_role AS ENUM ('biologist', 'reviewer', 'admin');

CREATE TABLE IF NOT EXISTS user_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role        app_role NOT NULL DEFAULT 'biologist',
    granted_by  UUID REFERENCES auth.users(id),
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, role)
);

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION auth_uid() RETURNS UUID AS $$
    SELECT auth.uid()
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION has_role(required_role app_role) RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role = required_role
    )
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION is_reviewer_or_admin() RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid() AND role IN ('reviewer', 'admin')
    )
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ============================================================
-- RLS: biologist_profile
-- ============================================================

ALTER TABLE biologist_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY profile_public_read ON biologist_profile
    FOR SELECT TO anon, authenticated
    USING (
        visibility_status = 'active'
        AND verification_status IN ('verified', 'partial')
    );

CREATE POLICY profile_owner_all ON biologist_profile
    FOR ALL TO authenticated
    USING (auth_user_id = auth.uid())
    WITH CHECK (auth_user_id = auth.uid());

CREATE POLICY profile_reviewer_read ON biologist_profile
    FOR SELECT TO authenticated
    USING (is_reviewer_or_admin());

CREATE POLICY profile_reviewer_update ON biologist_profile
    FOR UPDATE TO authenticated
    USING (is_reviewer_or_admin())
    WITH CHECK (is_reviewer_or_admin());

-- ============================================================
-- RLS: credential_record
-- ============================================================

ALTER TABLE credential_record ENABLE ROW LEVEL SECURITY;

CREATE POLICY credential_public_read ON credential_record
    FOR SELECT TO anon, authenticated
    USING (
        verification_status IN ('verified', 'partial')
        AND EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = credential_record.profile_id
            AND bp.visibility_status = 'active'
            AND bp.verification_status IN ('verified', 'partial')
        )
    );

CREATE POLICY credential_owner_all ON credential_record
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = credential_record.profile_id
            AND bp.auth_user_id = auth.uid()
        )
    );

CREATE POLICY credential_reviewer_read ON credential_record
    FOR SELECT TO authenticated
    USING (is_reviewer_or_admin());

CREATE POLICY credential_reviewer_update ON credential_record
    FOR UPDATE TO authenticated
    USING (is_reviewer_or_admin());

-- ============================================================
-- RLS: experience_evidence
-- ============================================================

ALTER TABLE experience_evidence ENABLE ROW LEVEL SECURITY;

CREATE POLICY evidence_public_read ON experience_evidence
    FOR SELECT TO anon, authenticated
    USING (
        is_verified = TRUE
        AND EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = experience_evidence.profile_id
            AND bp.visibility_status = 'active'
            AND bp.verification_status IN ('verified', 'partial')
        )
    );

CREATE POLICY evidence_owner_all ON experience_evidence
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = experience_evidence.profile_id
            AND bp.auth_user_id = auth.uid()
        )
    );

CREATE POLICY evidence_reviewer_read ON experience_evidence
    FOR SELECT TO authenticated
    USING (is_reviewer_or_admin());

CREATE POLICY evidence_reviewer_update ON experience_evidence
    FOR UPDATE TO authenticated
    USING (is_reviewer_or_admin());

-- ============================================================
-- RLS: verification_audit_log (APPEND-ONLY)
-- ============================================================

ALTER TABLE verification_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_insert_reviewer ON verification_audit_log
    FOR INSERT TO authenticated
    WITH CHECK (is_reviewer_or_admin());

CREATE POLICY audit_insert_system ON verification_audit_log
    FOR INSERT TO authenticated
    WITH CHECK (changed_by = 'system');

CREATE POLICY audit_read_reviewer ON verification_audit_log
    FOR SELECT TO authenticated
    USING (is_reviewer_or_admin());

CREATE POLICY audit_read_owner ON verification_audit_log
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = verification_audit_log.profile_id
            AND bp.auth_user_id = auth.uid()
        )
    );

-- No UPDATE or DELETE policies = immutable audit log

-- ============================================================
-- RENDER PAYLOAD CACHE (Alexander's recommendation)
-- ============================================================

CREATE TABLE IF NOT EXISTS render_payload_cache (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id          UUID NOT NULL REFERENCES biologist_profile(id)
                        ON DELETE CASCADE,
    render_payload_json JSONB NOT NULL,
    render_payload_hash TEXT NOT NULL,
    translation_version TEXT NOT NULL DEFAULT 'TE_v1.0',
    generated_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE(profile_id, translation_version)
);

CREATE INDEX idx_cache_profile ON render_payload_cache(profile_id);

ALTER TABLE render_payload_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY cache_public_read ON render_payload_cache
    FOR SELECT TO anon, authenticated
    USING (
        EXISTS (
            SELECT 1 FROM biologist_profile bp
            WHERE bp.id = render_payload_cache.profile_id
            AND bp.visibility_status = 'active'
            AND bp.verification_status IN ('verified', 'partial')
        )
    );

-- ============================================================
-- STORAGE BUCKETS (run via Supabase Dashboard or API)
-- ============================================================

-- Bucket: credentials_docs
--   Private by default
--   Signed URLs only for reviewers
--   Public never sees raw documents

-- Bucket: evidence_docs
--   Same rules as credentials_docs

-- Storage policies (Supabase Storage RLS):
-- INSERT: authenticated user where profile owner
-- SELECT: reviewer/admin only (signed URLs)
-- DELETE: admin only

-- ============================================================
-- SUBMISSION GATING FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION can_submit_for_review(p_profile_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    cred_count INTEGER;
    evidence_count INTEGER;
    doc_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO cred_count
    FROM credential_record
    WHERE profile_id = p_profile_id
    AND credential_type IN ('degree', 'license', 'certification');

    SELECT COUNT(*) INTO evidence_count
    FROM experience_evidence
    WHERE profile_id = p_profile_id;

    SELECT COUNT(*) INTO doc_count
    FROM credential_record
    WHERE profile_id = p_profile_id
    AND documentation_url IS NOT NULL;

    RETURN cred_count >= 1 AND evidence_count >= 3 AND doc_count >= 1;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
