-- BioCred — tighten table-level grants for the anonymous role
-- Idempotent. Safe to re-run.
--
-- Why this exists:
--   Supabase's default is GRANT ALL ON TABLES TO anon. RLS is the real gate,
--   but the anon key sits in the browser. If RLS is ever off on user_roles or
--   verification_audit_log, that default grant is enough for a stranger to
--   make themselves a reviewer or rewrite the audit trail.
--
-- This file does not replace RLS. It removes privileges anon has no legitimate
-- reason to hold, so a missing ENABLE ROW LEVEL SECURITY is not a full breach.

-- ============================================================
-- 1. Make sure RLS is on for every public table
-- ============================================================

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND NOT c.relrowsecurity
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.relname);
        RAISE NOTICE 'enabled RLS on %', r.relname;
    END LOOP;
END $$;

-- Do not FORCE RLS. The cache refresh job and review RPCs run as the
-- table owner / security definer; FORCE would make those fail unless a
-- matching write policy exists, and none does on render_payload_cache.

-- ============================================================
-- 2. Anon must not write anywhere
-- ============================================================

REVOKE ALL ON TABLE public.user_roles FROM anon, PUBLIC;
REVOKE ALL ON TABLE public.verification_audit_log FROM anon, PUBLIC;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
    ON TABLE
        public.biologist_profile,
        public.credential_record,
        public.experience_evidence,
        public.render_payload_cache
    FROM anon, PUBLIC;

-- document_submissions may or may not exist on a given environment.
DO $$
BEGIN
    IF to_regclass('public.document_submissions') IS NOT NULL THEN
        EXECUTE 'REVOKE ALL ON TABLE public.document_submissions FROM anon, PUBLIC';
        EXECUTE 'ALTER TABLE public.document_submissions ENABLE ROW LEVEL SECURITY';
    END IF;
END $$;

-- Views: SELECT only. Anon never writes a view.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLE
    public.profile_public_v1,
    public.credential_public_v1,
    public.evidence_public_v1,
    public.profile_render_v1
FROM anon, PUBLIC;

GRANT SELECT ON TABLE
    public.profile_public_v1,
    public.credential_public_v1,
    public.evidence_public_v1,
    public.profile_render_v1
TO anon, authenticated;

-- Base-table SELECT stays: the public views are SECURITY INVOKER on this
-- project, so anon still needs SELECT on the underlying tables. RLS policies
-- (profile_public_read etc.) are what hide unpublished rows.

GRANT SELECT ON TABLE
    public.biologist_profile,
    public.credential_record,
    public.experience_evidence,
    public.render_payload_cache
TO anon, authenticated;

-- Authenticated still needs the grants the intake / reviewer pages use.
GRANT SELECT, INSERT ON TABLE public.user_roles TO authenticated;
GRANT SELECT ON TABLE public.verification_audit_log TO authenticated;
