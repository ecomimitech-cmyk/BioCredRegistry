-- ============================================================
-- BioCred M5 — correction and resubmission after a rejection
-- ============================================================
-- Two changes, both in submit_profile_for_review:
--
--   1. A rejected profile can be corrected and sent back. Until now a rejection
--      was terminal: the reviewer could say no, and the biologist had no route
--      back. A registry where "no" is permanent is not a registry anyone will
--      sign up to.
--
--   2. Submission is refused from any status other than draft or rejected.
--      The function previously accepted a profile in any state, so calling it
--      on an approved profile silently pulled it off the public registry and
--      put it back in the queue. The page now hides that button, but a hidden
--      button is not a rule — the rule belongs here.
--
-- Idempotent: safe to re-run.
-- ============================================================

BEGIN;

-- The one-argument version has to go rather than be replaced: once the note
-- parameter exists with a default, a one-argument call matches both and
-- Postgres refuses it as ambiguous.
DROP FUNCTION IF EXISTS submit_profile_for_review(UUID);

CREATE OR REPLACE FUNCTION submit_profile_for_review(
    p_profile_id UUID,
    p_note       TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_owned  BOOLEAN;
    v_status verification_status;
    v_note   TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM biologist_profile
        WHERE id = p_profile_id AND auth_user_id = auth.uid()
    ) INTO v_owned;

    IF NOT v_owned THEN
        RAISE EXCEPTION 'not_profile_owner';
    END IF;

    SELECT verification_status INTO v_status
    FROM biologist_profile
    WHERE id = p_profile_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'profile_not_found';
    END IF;

    -- 'submitted' is the draft state; 'rejected' is a correction coming back.
    -- Everything else is either already queued or already decided.
    IF v_status NOT IN ('submitted', 'rejected') THEN
        RAISE EXCEPTION 'not_submittable_from_%', v_status;
    END IF;

    IF NOT can_submit_for_review(p_profile_id) THEN
        RAISE EXCEPTION 'submit_requirements_not_met';
    END IF;

    v_note := NULLIF(btrim(COALESCE(p_note, '')), '');

    -- A rejection has to carry a reason. A retry has to carry what changed, or
    -- the reviewer is re-reading the same file with no idea what to look at.
    IF v_status = 'rejected' AND v_note IS NULL THEN
        RAISE EXCEPTION 'resubmission_note_required';
    END IF;

    PERFORM set_config(
        'biocred.change_reason',
        CASE
            WHEN v_status = 'rejected'
                THEN 'resubmitted after rejection: ' || v_note
            ELSE COALESCE('submitted for review: ' || v_note, 'submitted for review')
        END,
        true
    );

    UPDATE biologist_profile
    SET verification_status = 'pending_review',
        updated_at = now()
    WHERE id = p_profile_id;

    -- Records already marked verified stay verified; there is no reason to make
    -- a reviewer re-check something they already approved.
    UPDATE credential_record
    SET verification_status = 'pending_review'
    WHERE profile_id = p_profile_id
      AND verification_status IN ('submitted', 'rejected');

    UPDATE experience_evidence
    SET verification_status = 'pending_review'
    WHERE profile_id = p_profile_id
      AND verification_status IN ('submitted', 'rejected');

    RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION submit_profile_for_review(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION submit_profile_for_review(UUID, TEXT) TO authenticated;

COMMIT;
