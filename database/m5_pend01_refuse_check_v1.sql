-- ============================================================
-- BioCred M5 — a pending profile the public page must refuse
-- ============================================================
-- PEND99 used to be that check. On 14 Oct 2026 it was marked
-- partial, so it became public. That decision is left alone:
-- undoing it here would skip the review path.
--
-- This creates PEND01 instead: pending, not public, and named
-- so a reviewer can see it is not for approving. The walkthrough
-- now opens this id.
--
-- Idempotent: safe to re-run. If PEND01 already exists, it is
-- put back to pending_review / draft.
-- ============================================================

BEGIN;

INSERT INTO public.biologist_profile (
    registry_id,
    full_name,
    professional_title,
    organization,
    visibility_status,
    verification_status,
    bio_summary
)
SELECT
    'PEND01',
    'Walkthrough Refuse Check',
    'Do not approve — public refuse check',
    'BioCred staging',
    'draft',
    'pending_review',
    'Dedicated walkthrough check. Opening this registry ID on the public page must refuse. Do not approve this profile.'
WHERE NOT EXISTS (
    SELECT 1 FROM public.biologist_profile WHERE registry_id = 'PEND01'
);

UPDATE public.biologist_profile
SET verification_status = 'pending_review',
    visibility_status   = 'draft',
    full_name           = 'Walkthrough Refuse Check',
    professional_title  = 'Do not approve — public refuse check',
    organization        = 'BioCred staging',
    bio_summary         = 'Dedicated walkthrough check. Opening this registry ID on the public page must refuse. Do not approve this profile.',
    updated_at          = now()
WHERE registry_id = 'PEND01';

DO $$
DECLARE
    v_exists   INT;
    v_public   INT;
    v_render   INT;
    v_status   TEXT;
    v_visible  TEXT;
BEGIN
    SELECT count(*), min(verification_status::text), min(visibility_status::text)
      INTO v_exists, v_status, v_visible
    FROM public.biologist_profile
    WHERE registry_id = 'PEND01';

    IF v_exists = 0 THEN
        RAISE EXCEPTION 'rolled back: PEND01 was not created';
    END IF;

    SET LOCAL ROLE anon;

    SELECT count(*) INTO v_public
    FROM public.profile_public_v1
    WHERE registry_id = 'PEND01';

    SELECT count(*) INTO v_render
    FROM public.profile_render_v1
    WHERE registry_id = 'PEND01';

    RESET ROLE;

    IF v_public > 0 OR v_render > 0 THEN
        RAISE EXCEPTION
            'rolled back: anon can still see PEND01 (public %, render %). Status is %, visibility is %',
            v_public, v_render, v_status, v_visible;
    END IF;

    RAISE NOTICE
        'PEND01 is pending and invisible to anon (status %, visibility %). Public refuse check is ready.',
        v_status, v_visible;
END
$$;

COMMIT;
