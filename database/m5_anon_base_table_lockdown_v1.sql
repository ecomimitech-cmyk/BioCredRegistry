-- ============================================================
-- BioCred M5 QA — close the anonymous read on the base tables
-- ============================================================
-- Found by the anonymous probe in qa/anon_probe_v1.ps1.
--
-- With nothing but the publishable key from the page source, a stranger could
-- read credential_record directly — including documentation_url, the storage
-- path of every uploaded document:
--
--   b2413861-…/f10862fd-…/2026-08-11_smoke-degree.pdf
--
-- The file itself stays shut: storage refused every unsigned request in the same
-- run. But the path carries the owner's auth user id and the original filename,
-- and on staging those filenames are invented. On a real registry they read
-- "jane-smith-phd-diploma.pdf". credential_public_v1 deliberately omits this
-- column; reading the base table walked around the view that was protecting it.
--
-- Nothing anonymous needs these tables: every public page reads the _public_v1
-- views. Only the reviewer portal and the intake form touch the base tables, and
-- both run signed in, so `authenticated` keeps its grant.
--
-- The transaction verifies itself. If revoking breaks the public views — which
-- would happen if they run with the caller's privileges rather than the owner's —
-- the checks below fail and the whole thing rolls back, leaving staging exactly
-- as it was.
--
-- Idempotent: safe to re-run.
-- ============================================================

BEGIN;

REVOKE SELECT ON TABLE
    public.biologist_profile,
    public.credential_record,
    public.experience_evidence,
    public.render_payload_cache
FROM anon, PUBLIC;

-- Signed-in pages still need these.
GRANT SELECT ON TABLE
    public.biologist_profile,
    public.credential_record,
    public.experience_evidence,
    public.render_payload_cache
TO authenticated;

DO $$
DECLARE
    v_profiles INT;
    v_creds    INT;
    v_evidence INT;
    v_render   INT;
    v_leak     INT;
BEGIN
    -- Stand in the shoes of a stranger with the publishable key.
    SET LOCAL ROLE anon;

    SELECT count(*) INTO v_profiles FROM public.profile_public_v1;
    SELECT count(*) INTO v_creds    FROM public.credential_public_v1;
    SELECT count(*) INTO v_evidence FROM public.evidence_public_v1;
    SELECT count(*) INTO v_render   FROM public.profile_render_v1;

    BEGIN
        SELECT count(*) INTO v_leak FROM public.credential_record;
    EXCEPTION WHEN insufficient_privilege THEN
        v_leak := 0;
    END;

    RESET ROLE;

    IF v_profiles = 0 THEN
        RAISE EXCEPTION 'rolled back: the public directory went empty (profile_public_v1 returned 0 rows to anon)';
    END IF;
    IF v_creds = 0 OR v_evidence = 0 THEN
        RAISE EXCEPTION 'rolled back: public profile pages lost their credentials or evidence (% creds, % evidence)', v_creds, v_evidence;
    END IF;
    IF v_render = 0 THEN
        RAISE EXCEPTION 'rolled back: the experience map lost its data (profile_render_v1 returned 0 rows to anon)';
    END IF;
    IF v_leak > 0 THEN
        RAISE EXCEPTION 'rolled back: anon can still read credential_record (% rows) — the revoke did not take', v_leak;
    END IF;

    RAISE NOTICE 'Public surface intact: % profiles, % credentials, % evidence rows, % render rows. Base tables now closed to anon.',
        v_profiles, v_creds, v_evidence, v_render;
END
$$;

COMMIT;
