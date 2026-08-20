-- BioCred — Storage buckets + RLS (from docs/storage_policy_plan_v1.md)
-- Apply on staging/production after schema + supabase_rls.sql
-- Idempotent: safe to re-run

-- ============================================================
-- BUCKETS (private)
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  (
    'credentials_docs',
    'credentials_docs',
    false,
    10485760,
    ARRAY['application/pdf', 'image/jpeg', 'image/png']::text[]
  ),
  (
    'evidence_docs',
    'evidence_docs',
    false,
    10485760,
    ARRAY['application/pdf', 'image/jpeg', 'image/png']::text[]
  )
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ============================================================
-- HELPER: first path segment = profile UUID
-- Path: "{profile_id}/{credential_or_evidence_id}/{filename}"
-- ============================================================

CREATE OR REPLACE FUNCTION storage_profile_id(name TEXT)
RETURNS UUID AS $$
  SELECT NULLIF(split_part(name, '/', 1), '')::uuid
$$ LANGUAGE sql IMMUTABLE;

-- ============================================================
-- Drop existing storage policies (idempotent re-apply)
-- ============================================================

DROP POLICY IF EXISTS storage_credentials_owner_insert ON storage.objects;
DROP POLICY IF EXISTS storage_credentials_owner_read ON storage.objects;
DROP POLICY IF EXISTS storage_credentials_reviewer_read ON storage.objects;
DROP POLICY IF EXISTS storage_credentials_admin_delete ON storage.objects;
DROP POLICY IF EXISTS storage_evidence_owner_insert ON storage.objects;
DROP POLICY IF EXISTS storage_evidence_owner_read ON storage.objects;
DROP POLICY IF EXISTS storage_evidence_reviewer_read ON storage.objects;
DROP POLICY IF EXISTS storage_evidence_admin_delete ON storage.objects;

-- ============================================================
-- credentials_docs
-- ============================================================

CREATE POLICY storage_credentials_owner_insert
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'credentials_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_credentials_owner_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_credentials_reviewer_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND is_reviewer_or_admin()
);

CREATE POLICY storage_credentials_admin_delete
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'credentials_docs'
  AND has_role('admin')
);

-- ============================================================
-- evidence_docs
-- ============================================================

CREATE POLICY storage_evidence_owner_insert
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'evidence_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_evidence_owner_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND EXISTS (
    SELECT 1 FROM biologist_profile bp
    WHERE bp.id = storage_profile_id(name)
      AND bp.auth_user_id = auth.uid()
  )
);

CREATE POLICY storage_evidence_reviewer_read
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND is_reviewer_or_admin()
);

CREATE POLICY storage_evidence_admin_delete
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'evidence_docs'
  AND has_role('admin')
);

-- ============================================================
-- Auth bootstrap helpers (M2 intake)
-- Biologist can claim own biologist role; RPC links profile
-- ============================================================

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_roles_self_read ON user_roles;
DROP POLICY IF EXISTS user_roles_self_insert_biologist ON user_roles;
DROP POLICY IF EXISTS user_roles_admin_all ON user_roles;

CREATE POLICY user_roles_self_read ON user_roles
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY user_roles_self_insert_biologist ON user_roles
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND role = 'biologist'
  );

CREATE POLICY user_roles_admin_all ON user_roles
  FOR ALL TO authenticated
  USING (has_role('admin'))
  WITH CHECK (has_role('admin'));

GRANT SELECT, INSERT ON user_roles TO authenticated;

-- Ensure biologist role row exists for current user
CREATE OR REPLACE FUNCTION ensure_biologist_role()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO user_roles (user_id, role)
  VALUES (auth.uid(), 'biologist')
  ON CONFLICT (user_id, role) DO NOTHING;
END;
$$;

REVOKE ALL ON FUNCTION ensure_biologist_role() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ensure_biologist_role() TO authenticated;

-- Submit profile for review when gating function passes
CREATE OR REPLACE FUNCTION submit_profile_for_review(p_profile_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  owned BOOLEAN;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM biologist_profile
    WHERE id = p_profile_id AND auth_user_id = auth.uid()
  ) INTO owned;

  IF NOT owned THEN
    RAISE EXCEPTION 'not_profile_owner';
  END IF;

  IF NOT can_submit_for_review(p_profile_id) THEN
    RAISE EXCEPTION 'submit_requirements_not_met';
  END IF;

  UPDATE biologist_profile
  SET verification_status = 'pending_review',
      updated_at = now()
  WHERE id = p_profile_id;

  UPDATE credential_record
  SET verification_status = 'pending_review'
  WHERE profile_id = p_profile_id
    AND verification_status = 'submitted';

  UPDATE experience_evidence
  SET verification_status = 'pending_review'
  WHERE profile_id = p_profile_id
    AND verification_status = 'submitted';

  RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION submit_profile_for_review(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION submit_profile_for_review(UUID) TO authenticated;

GRANT EXECUTE ON FUNCTION can_submit_for_review(UUID) TO authenticated;
