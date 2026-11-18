-- BioCred M3 — Reviewer decision layer
-- Apply after schema.sql + supabase_rls.sql + migrations/2026_06_block1_* + storage_policies.sql
-- Idempotent: safe to re-run.
--
-- What this adds:
--   1. A real reason on every audit row (the Block 1 trigger hardcoded 'auto_trigger')
--   2. review_start()  — reviewer claims a submission
--   3. review_decide() — verified / partial / rejected, enforced in the database
--   4. grant_role_by_email() — bootstrap only, NOT callable from the browser

-- ============================================================
-- 1. Audit reason plumbing
-- ============================================================
-- The Block 1 trigger already logs every verification_status change, but it
-- wrote 'auto_trigger' as the reason, which tells a future auditor nothing.
-- The decision RPCs below set a transaction-local GUC that the trigger now
-- reads, so the reviewer's stated reason lands on the audit row itself.
-- Any status change made outside those RPCs still falls back to 'auto_trigger',
-- which is exactly the signal you'd want: a change nobody justified.

CREATE OR REPLACE FUNCTION biocred_log_verification_status_change()
RETURNS TRIGGER AS $$
DECLARE
    v_profile_id UUID;
    v_credential_id UUID;
    v_reason TEXT;
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

    v_reason := COALESCE(
        NULLIF(current_setting('biocred.change_reason', true), ''),
        'auto_trigger'
    );

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
        v_reason
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- 2. review_start — reviewer claims a pending submission
-- ============================================================

CREATE OR REPLACE FUNCTION review_start(p_profile_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_status verification_status;
BEGIN
    IF NOT is_reviewer_or_admin() THEN
        RAISE EXCEPTION 'not_a_reviewer';
    END IF;

    SELECT verification_status INTO v_status
    FROM biologist_profile WHERE id = p_profile_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'profile_not_found';
    END IF;

    IF v_status <> 'pending_review' THEN
        RAISE EXCEPTION 'profile_not_pending';
    END IF;

    PERFORM set_config('biocred.change_reason', 'Review started', true);

    UPDATE biologist_profile
    SET verification_status = 'under_verification',
        updated_at = now()
    WHERE id = p_profile_id;

    RETURN TRUE;
END;
$$;

-- ============================================================
-- 3. review_decide — the actual decision
-- ============================================================
-- Rules enforced here rather than in the page:
--   * reviewers only
--   * only a submission that is pending_review or under_verification
--   * a rejection or a partial MUST carry a reason — an unexplained refusal is
--     useless to the biologist and indefensible to an agency
--   * only an approved profile is ever made publicly visible

CREATE OR REPLACE FUNCTION review_decide(
    p_profile_id UUID,
    p_decision   TEXT,
    p_reason     TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_status     verification_status;
    v_new_status verification_status;
    v_reason     TEXT;
BEGIN
    IF NOT is_reviewer_or_admin() THEN
        RAISE EXCEPTION 'not_a_reviewer';
    END IF;

    v_new_status := CASE p_decision
        WHEN 'approve'  THEN 'verified'::verification_status
        WHEN 'partial'  THEN 'partial'::verification_status
        WHEN 'reject'   THEN 'rejected'::verification_status
        ELSE NULL
    END;

    IF v_new_status IS NULL THEN
        RAISE EXCEPTION 'invalid_decision';
    END IF;

    v_reason := NULLIF(btrim(COALESCE(p_reason, '')), '');

    IF v_new_status IN ('rejected', 'partial') AND v_reason IS NULL THEN
        RAISE EXCEPTION 'reason_required';
    END IF;

    SELECT verification_status INTO v_status
    FROM biologist_profile WHERE id = p_profile_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'profile_not_found';
    END IF;

    IF v_status NOT IN ('pending_review', 'under_verification') THEN
        RAISE EXCEPTION 'profile_not_reviewable';
    END IF;

    PERFORM set_config(
        'biocred.change_reason',
        COALESCE(v_reason, 'Approved — documentation reviewed'),
        true
    );

    UPDATE biologist_profile
    SET verification_status = v_new_status,
        visibility_status = CASE
            WHEN v_new_status IN ('verified', 'partial') THEN 'active'::visibility_status
            ELSE visibility_status
        END,
        updated_at = now()
    WHERE id = p_profile_id;

    UPDATE credential_record
    SET verification_status = v_new_status,
        verification_method = 'document_review',
        verification_date   = CURRENT_DATE,
        verified_by         = COALESCE(auth.uid()::text, 'system'),
        audit_notes         = v_reason
    WHERE profile_id = p_profile_id
      AND verification_status IN ('pending_review', 'under_verification', 'submitted');

    UPDATE experience_evidence
    SET verification_status = v_new_status
    WHERE profile_id = p_profile_id
      AND verification_status IN ('pending_review', 'under_verification', 'submitted');

    RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION review_start(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION review_decide(UUID, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION review_start(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION review_decide(UUID, TEXT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION is_reviewer_or_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION has_role(app_role) TO authenticated;

-- The reviewer portal reads the audit trail. RLS still decides which rows come
-- back (reviewers see all, a biologist sees only their own), but the table-level
-- grant has to exist for the policy to ever be consulted.
GRANT SELECT ON verification_audit_log TO authenticated;

-- ============================================================
-- 4. Role bootstrap — deliberately unreachable from the browser
-- ============================================================
-- There is no self-service path to becoming a reviewer, and there should not be.
-- This is granted to nobody: run it from psql as the database owner.
--
--   SELECT grant_role_by_email('reviewer@example.com', 'reviewer');

CREATE OR REPLACE FUNCTION grant_role_by_email(p_email TEXT, p_role app_role)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    SELECT id INTO v_user_id FROM auth.users WHERE lower(email) = lower(p_email);

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'no_such_user: %', p_email;
    END IF;

    INSERT INTO user_roles (user_id, role)
    VALUES (v_user_id, p_role)
    ON CONFLICT (user_id, role) DO NOTHING;

    RETURN v_user_id;
END;
$$;

REVOKE ALL ON FUNCTION grant_role_by_email(TEXT, app_role) FROM PUBLIC;
-- no GRANT: not callable by anon or authenticated, by design
