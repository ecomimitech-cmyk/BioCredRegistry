-- BioCred Block 1 (June 2026) — evidence verification_status + public views + audit triggers
-- Apply after schema.sql + supabase_rls.sql on staging/production.
-- Safe to re-run: uses IF NOT EXISTS / DROP IF EXISTS where practical.

-- ============================================================
-- 1. experience_evidence.verification_status (replaces is_verified)
-- ============================================================

ALTER TABLE experience_evidence
    ADD COLUMN IF NOT EXISTS verification_status verification_status
    DEFAULT 'submitted';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'experience_evidence' AND column_name = 'is_verified'
    ) THEN
        UPDATE experience_evidence
        SET verification_status = CASE
            WHEN is_verified IS TRUE THEN 'verified'::verification_status
            ELSE 'submitted'::verification_status
        END
        WHERE verification_status IS NULL
           OR verification_status = 'submitted'::verification_status;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_evidence_verified;

ALTER TABLE experience_evidence
    DROP COLUMN IF EXISTS is_verified;

CREATE INDEX IF NOT EXISTS idx_evidence_verification
    ON experience_evidence(verification_status);

-- ============================================================
-- 2. Public-safe views (registry_id → render payload)
-- ============================================================

CREATE OR REPLACE VIEW public.profile_public_v1 AS
SELECT
    bp.id,
    bp.registry_id,
    bp.full_name,
    bp.professional_title,
    bp.organization,
    bp.state,
    bp.city,
    bp.geographic_region,
    bp.years_experience,
    bp.primary_discipline,
    bp.taxonomic_focus,
    bp.bio_summary,
    bp.verification_status,
    bp.profile_photo_url,
    bp.created_at,
    bp.updated_at
FROM biologist_profile bp
WHERE bp.visibility_status = 'active'
  AND bp.verification_status IN ('verified', 'partial');

CREATE OR REPLACE VIEW public.credential_public_v1 AS
SELECT
    cr.id,
    cr.profile_id,
    cr.credential_type,
    cr.title,
    cr.issuing_authority,
    cr.year_issued,
    cr.verification_status,
    cr.verification_method,
    cr.verification_date
FROM credential_record cr
INNER JOIN biologist_profile bp ON bp.id = cr.profile_id
WHERE cr.verification_status IN ('verified', 'partial')
  AND bp.visibility_status = 'active'
  AND bp.verification_status IN ('verified', 'partial');

CREATE OR REPLACE VIEW public.evidence_public_v1 AS
SELECT
    ee.id,
    ee.profile_id,
    ee.domain_category,
    ee.activity_type,
    ee.species_or_system,
    ee.habitat_context,
    ee.project_type,
    ee.years_applied,
    ee.role_level,
    ee.evidence_source,
    ee.verification_status,
    ee.translation_version,
    ee.created_at
FROM experience_evidence ee
INNER JOIN biologist_profile bp ON bp.id = ee.profile_id
WHERE ee.verification_status IN ('verified', 'partial')
  AND bp.visibility_status = 'active'
  AND bp.verification_status IN ('verified', 'partial');

CREATE OR REPLACE VIEW public.profile_render_v1 AS
SELECT
    bp.registry_id,
    bp.full_name,
    bp.verification_status AS profile_verification_status,
    rpc.render_payload_json,
    rpc.render_payload_hash,
    rpc.translation_version,
    rpc.generated_at
FROM biologist_profile bp
INNER JOIN render_payload_cache rpc
    ON rpc.profile_id = bp.id
WHERE bp.visibility_status = 'active'
  AND bp.verification_status IN ('verified', 'partial');

GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.profile_public_v1 TO anon, authenticated;
GRANT SELECT ON public.credential_public_v1 TO anon, authenticated;
GRANT SELECT ON public.evidence_public_v1 TO anon, authenticated;
GRANT SELECT ON public.profile_render_v1 TO anon, authenticated;

-- ============================================================
-- 3. Audit log triggers (verification_status changes)
-- ============================================================

CREATE OR REPLACE FUNCTION biocred_log_verification_status_change()
RETURNS TRIGGER AS $$
DECLARE
    v_profile_id UUID;
    v_credential_id UUID;
BEGIN
    IF OLD.verification_status IS NOT DISTINCT FROM NEW.verification_status THEN
        RETURN NEW;
    END IF;

    v_credential_id := NULL;
    v_profile_id := NULL;

    IF TG_TABLE_NAME = 'biologist_profile' THEN
        v_profile_id := NEW.id;
    ELSIF TG_TABLE_NAME = 'credential_record' THEN
        v_profile_id := NEW.profile_id;
        v_credential_id := NEW.id;
    ELSIF TG_TABLE_NAME = 'experience_evidence' THEN
        v_profile_id := NEW.profile_id;
    ELSE
        RETURN NEW;
    END IF;

    INSERT INTO verification_audit_log (
        profile_id,
        credential_id,
        previous_status,
        new_status,
        changed_by,
        change_reason
    ) VALUES (
        v_profile_id,
        v_credential_id,
        OLD.verification_status,
        NEW.verification_status,
        COALESCE(auth.uid()::text, 'system'),
        'auto_trigger'
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_profile_verification_audit ON biologist_profile;
CREATE TRIGGER trg_profile_verification_audit
    AFTER UPDATE OF verification_status ON biologist_profile
    FOR EACH ROW
    EXECUTE FUNCTION biocred_log_verification_status_change();

DROP TRIGGER IF EXISTS trg_credential_verification_audit ON credential_record;
CREATE TRIGGER trg_credential_verification_audit
    AFTER UPDATE OF verification_status ON credential_record
    FOR EACH ROW
    EXECUTE FUNCTION biocred_log_verification_status_change();

DROP TRIGGER IF EXISTS trg_evidence_verification_audit ON experience_evidence;
CREATE TRIGGER trg_evidence_verification_audit
    AFTER UPDATE OF verification_status ON experience_evidence
    FOR EACH ROW
    EXECUTE FUNCTION biocred_log_verification_status_change();

-- ============================================================
-- 4. Verified-record edit lock
-- ============================================================

CREATE OR REPLACE FUNCTION biocred_reject_verified_field_edits()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.verification_status = 'verified'::verification_status THEN
        IF TG_TABLE_NAME = 'biologist_profile' THEN
            IF NEW.full_name IS DISTINCT FROM OLD.full_name
               OR NEW.registry_id IS DISTINCT FROM OLD.registry_id
               OR NEW.professional_title IS DISTINCT FROM OLD.professional_title
               OR NEW.organization IS DISTINCT FROM OLD.organization
               OR NEW.bio_summary IS DISTINCT FROM OLD.bio_summary
               OR NEW.visibility_status IS DISTINCT FROM OLD.visibility_status
            THEN
                RAISE EXCEPTION 'Verified profile rows require re-review before editing core fields';
            END IF;
        ELSIF TG_TABLE_NAME = 'credential_record' THEN
            IF NEW.title IS DISTINCT FROM OLD.title
               OR NEW.credential_type IS DISTINCT FROM OLD.credential_type
               OR NEW.issuing_authority IS DISTINCT FROM OLD.issuing_authority
               OR NEW.documentation_url IS DISTINCT FROM OLD.documentation_url
            THEN
                RAISE EXCEPTION 'Verified credential rows require re-review before editing core fields';
            END IF;
        ELSIF TG_TABLE_NAME = 'experience_evidence' THEN
            IF NEW.domain_category IS DISTINCT FROM OLD.domain_category
               OR NEW.activity_type IS DISTINCT FROM OLD.activity_type
               OR NEW.years_applied IS DISTINCT FROM OLD.years_applied
               OR NEW.role_level IS DISTINCT FROM OLD.role_level
            THEN
                RAISE EXCEPTION 'Verified evidence rows require re-review before editing core fields';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_profile_verified_edit_lock ON biologist_profile;
CREATE TRIGGER trg_profile_verified_edit_lock
    BEFORE UPDATE ON biologist_profile
    FOR EACH ROW
    EXECUTE FUNCTION biocred_reject_verified_field_edits();

DROP TRIGGER IF EXISTS trg_credential_verified_edit_lock ON credential_record;
CREATE TRIGGER trg_credential_verified_edit_lock
    BEFORE UPDATE ON credential_record
    FOR EACH ROW
    EXECUTE FUNCTION biocred_reject_verified_field_edits();

DROP TRIGGER IF EXISTS trg_evidence_verified_edit_lock ON experience_evidence;
CREATE TRIGGER trg_evidence_verified_edit_lock
    BEFORE UPDATE ON experience_evidence
    FOR EACH ROW
    EXECUTE FUNCTION biocred_reject_verified_field_edits();
