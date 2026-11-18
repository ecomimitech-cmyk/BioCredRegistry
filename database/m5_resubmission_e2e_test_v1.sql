-- ============================================================
-- BioCred M5 — correction and resubmission, end to end (TEST ONLY)
-- ============================================================
-- Runs the whole loop against SM7523 as the three real roles, each with its
-- real permissions, and then ROLLS EVERYTHING BACK. Nothing changes on
-- staging: not the profile, not the audit log, not the public page.
--
--   setup     SM7523 put back to pending_review   (as owner of the database)
--   1         reviewer starts review and rejects with a reason
--   2         anon: SM7523 is gone from the public view
--   3         biologist resubmits WITHOUT a note  → must be refused
--   4         biologist resubmits WITH a note     → accepted, audit row carries it
--   5         reviewer would see the "resubmitted" tag (a prior 'rejected' row exists)
--   6         reviewer starts review and approves
--   7         anon: SM7523 is back on the public view
--   8         biologist tries to resubmit a verified profile → must be refused
--
-- Run in the Supabase SQL Editor (it needs to read auth.users and switch roles).
-- Each step appends to a log. The script always ends by RAISING that log as an
-- error on purpose: the SQL Editor shows it, and the error forces the rollback.
-- A failing step raises its own message instead ("step N: ...").
-- ============================================================

BEGIN;

DO $$
DECLARE
    v_profile   UUID;
    v_bio       UUID;
    v_rev       UUID;
    v_status    TEXT;
    v_count     INT;
    v_reason    TEXT;
    v_err       TEXT;
    v_log       TEXT := 'M5 RESUBMISSION E2E';
BEGIN
    SELECT id, auth_user_id INTO v_profile, v_bio
    FROM public.biologist_profile WHERE registry_id = 'SM7523';
    SELECT id INTO v_rev FROM auth.users WHERE email = 'ainoa.m2smoke.dcf5f6@gmail.com';

    IF v_profile IS NULL OR v_bio IS NULL OR v_rev IS NULL THEN
        RAISE EXCEPTION 'setup: missing profile (%), biologist (%) or reviewer (%)', v_profile, v_bio, v_rev;
    END IF;

    -- setup ------------------------------------------------------------------
    PERFORM set_config('biocred.change_reason', 'QA e2e test setup (rolled back)', true);
    UPDATE public.biologist_profile
       SET verification_status = 'pending_review', updated_at = now()
     WHERE id = v_profile;
    v_log := v_log || chr(10) || format('setup     SM7523 -> pending_review');

    -- 1. reviewer rejects ----------------------------------------------------
    PERFORM set_config('request.jwt.claims', json_build_object('sub', v_rev, 'role', 'authenticated')::text, true);
    SET LOCAL ROLE authenticated;
    PERFORM public.review_start(v_profile);
    PERFORM public.review_decide(v_profile, 'reject', 'QA test: licence scan unreadable, please replace it.');
    RESET ROLE;
    SELECT verification_status::text INTO v_status FROM public.biologist_profile WHERE id = v_profile;
    IF v_status <> 'rejected' THEN RAISE EXCEPTION 'step 1: expected rejected, got %', v_status; END IF;
    v_log := v_log || chr(10) || format('step 1    reviewer rejected with a reason -> %s', v_status);

    -- 2. gone from the public view -------------------------------------------
    SET LOCAL ROLE anon;
    SELECT count(*) INTO v_count FROM public.profile_public_v1 WHERE registry_id = 'SM7523';
    RESET ROLE;
    IF v_count <> 0 THEN RAISE EXCEPTION 'step 2: rejected SM7523 still public (% rows)', v_count; END IF;
    v_log := v_log || chr(10) || format('step 2    anon cannot see rejected SM7523');

    -- 3. resubmit without a note: refused -------------------------------------
    PERFORM set_config('request.jwt.claims', json_build_object('sub', v_bio, 'role', 'authenticated')::text, true);
    SET LOCAL ROLE authenticated;
    v_err := NULL;
    BEGIN
        PERFORM public.submit_profile_for_review(v_profile, NULL);
    EXCEPTION WHEN others THEN
        v_err := SQLERRM;
    END;
    IF v_err IS NULL OR v_err NOT LIKE '%resubmission_note_required%' THEN
        RAISE EXCEPTION 'step 3: resubmission without note was not refused (got: %)', COALESCE(v_err, 'accepted');
    END IF;
    v_log := v_log || chr(10) || format('step 3    resubmission without a note refused: %s', v_err);

    -- 4. resubmit with a note: accepted ---------------------------------------
    PERFORM public.submit_profile_for_review(v_profile, 'Replaced the licence scan with a legible copy.');
    RESET ROLE;
    SELECT verification_status::text INTO v_status FROM public.biologist_profile WHERE id = v_profile;
    IF v_status <> 'pending_review' THEN RAISE EXCEPTION 'step 4: expected pending_review, got %', v_status; END IF;
    -- Every row written in one transaction shares the same created_at (now() is
    -- the transaction start), so "latest" is ambiguous here. Look for the row by
    -- its content instead.
    SELECT change_reason INTO v_reason FROM public.verification_audit_log
     WHERE profile_id = v_profile AND new_status = 'pending_review'
       AND change_reason LIKE 'resubmitted after rejection:%'
     LIMIT 1;
    IF v_reason IS NULL OR v_reason NOT LIKE 'resubmitted after rejection:%' THEN
        RAISE EXCEPTION 'step 4: audit row does not carry the note (got: %)', v_reason;
    END IF;
    v_log := v_log || chr(10) || format('step 4    resubmitted with a note -> %s, audit: "%s"', v_status, v_reason);

    -- 5. reviewer would see the "resubmitted" tag -----------------------------
    SELECT count(*) INTO v_count FROM public.verification_audit_log
     WHERE profile_id = v_profile AND new_status = 'rejected';
    IF v_count = 0 THEN RAISE EXCEPTION 'step 5: no prior rejected row, tag would not show'; END IF;
    v_log := v_log || chr(10) || format('step 5    prior rejection on record (%s row/s): queue shows "resubmitted"', v_count);

    -- 6. reviewer approves ----------------------------------------------------
    PERFORM set_config('request.jwt.claims', json_build_object('sub', v_rev, 'role', 'authenticated')::text, true);
    SET LOCAL ROLE authenticated;
    PERFORM public.review_start(v_profile);
    PERFORM public.review_decide(v_profile, 'approve', NULL);
    RESET ROLE;
    SELECT verification_status::text INTO v_status FROM public.biologist_profile WHERE id = v_profile;
    IF v_status <> 'verified' THEN RAISE EXCEPTION 'step 6: expected verified, got %', v_status; END IF;
    v_log := v_log || chr(10) || format('step 6    reviewer approved -> %s', v_status);

    -- 7. back on the public view ----------------------------------------------
    SET LOCAL ROLE anon;
    SELECT count(*) INTO v_count FROM public.profile_public_v1 WHERE registry_id = 'SM7523';
    RESET ROLE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'step 7: approved SM7523 not public (% rows)', v_count; END IF;
    v_log := v_log || chr(10) || format('step 7    anon sees SM7523 again');

    -- 8. a verified profile cannot be resubmitted -----------------------------
    PERFORM set_config('request.jwt.claims', json_build_object('sub', v_bio, 'role', 'authenticated')::text, true);
    SET LOCAL ROLE authenticated;
    v_err := NULL;
    BEGIN
        PERFORM public.submit_profile_for_review(v_profile, 'should be refused');
    EXCEPTION WHEN others THEN
        v_err := SQLERRM;
    END;
    RESET ROLE;
    IF v_err IS NULL OR v_err NOT LIKE '%not_submittable_from_%' THEN
        RAISE EXCEPTION 'step 8: verified profile was resubmittable (got: %)', COALESCE(v_err, 'accepted');
    END IF;
    v_log := v_log || chr(10) || format('step 8    verified profile cannot be resubmitted: %s', v_err);

    v_log := v_log || chr(10) || 'ALL 8 STEPS PASSED.';
    -- Raised on purpose: shows the log in the SQL Editor and guarantees the rollback.
    RAISE EXCEPTION '%', v_log;
END
$$;

ROLLBACK;
