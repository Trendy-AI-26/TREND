-- REVIEW ONLY: do not apply until the owner approves the execution plan.
-- Account-first serialization: every supported credit writer locks the same row
-- before reading reservation/terminal state. Independent users remain concurrent.
-- No existing data is updated by this migration; only function definitions/ACLs.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE OR REPLACE FUNCTION public.reserve_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_amount integer, p_idempotency_key text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_existing public.credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Preserve the existing initial-account allowance; never overwrite an account.
    INSERT INTO public.credit_accounts(user_id, balance, reserved)
    VALUES (p_user_id, COALESCE((SELECT image_credits FROM public.plans WHERE code = 'beta'), 15), 0)
    ON CONFLICT (user_id) DO NOTHING;
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM public.credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_ACCOUNT_NOT_FOUND'; END IF;

    SELECT * INTO v_existing FROM public.credit_ledger
    WHERE idempotency_key = p_idempotency_key;
    IF FOUND THEN
        IF v_existing.operation IS DISTINCT FROM 'reserve'
           OR v_existing.user_id IS DISTINCT FROM p_user_id
           OR v_existing.generation_id IS DISTINCT FROM p_generation_id
           OR v_existing.amount IS DISTINCT FROM p_amount THEN
            RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
        END IF;
        -- Replay the receipt, even after completion; never reopen the reservation.
        RETURN jsonb_build_object('reservation_id', p_idempotency_key,
            'user_id', p_user_id, 'generation_id', p_generation_id, 'amount', p_amount);
    END IF;

    IF v_balance - v_reserved < p_amount THEN RAISE EXCEPTION 'INSUFFICIENT_CREDITS'; END IF;
    UPDATE public.credit_accounts
    SET reserved = reserved + p_amount, updated_at = now() WHERE user_id = p_user_id;
    INSERT INTO public.credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'reserve', p_amount, p_idempotency_key,
        jsonb_build_object('amount', p_amount, 'generation_id', p_generation_id));
    RETURN jsonb_build_object('reservation_id', p_idempotency_key,
        'user_id', p_user_id, 'generation_id', p_generation_id, 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    -- Global key collision from another account: this block's mutations roll back.
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_reservation public.credit_ledger%ROWTYPE;
    v_commit public.credit_ledger%ROWTYPE;
    v_release public.credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_reservation_id IS NULL OR btrim(p_reservation_id) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Do not acquire a shared reservation lock before this account lock.
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM public.credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;

    SELECT * INTO v_reservation FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id;
    IF NOT FOUND OR v_reservation.operation IS DISTINCT FROM 'reserve'
       OR v_reservation.user_id IS DISTINCT FROM p_user_id
       OR v_reservation.generation_id IS DISTINCT FROM p_generation_id
       OR v_reservation.amount IS DISTINCT FROM p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    SELECT * INTO v_commit FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id || '-commit';
    SELECT * INTO v_release FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id || '-release';

    IF v_commit.id IS NOT NULL AND (
        v_commit.operation IS DISTINCT FROM 'commit'
        OR v_commit.user_id IS DISTINCT FROM p_user_id
        OR v_commit.generation_id IS DISTINCT FROM p_generation_id
        OR v_commit.amount IS DISTINCT FROM -p_amount
    ) THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED'; END IF;
    IF v_release.id IS NOT NULL AND (
        v_release.operation IS DISTINCT FROM 'release'
        OR v_release.user_id IS DISTINCT FROM p_user_id
        OR v_release.generation_id IS DISTINCT FROM p_generation_id
        OR v_release.amount IS DISTINCT FROM p_amount
    ) THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED'; END IF;
    IF v_commit.id IS NOT NULL AND v_release.id IS NOT NULL THEN
        -- Existing inconsistent history needs separate reconciliation, not silent repair.
        RAISE EXCEPTION 'CREDIT_RESERVATION_STATE_INVALID';
    END IF;

    IF v_commit.id IS NOT NULL THEN
        RETURN jsonb_build_object('status', 'committed', 'amount', p_amount);
    END IF;
    IF v_release.id IS NOT NULL THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_ALREADY_RELEASED';
    END IF;
    IF v_reserved < p_amount OR v_balance < p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    UPDATE public.credit_accounts
    SET balance = balance - p_amount, reserved = reserved - p_amount, updated_at = now()
    WHERE user_id = p_user_id;
    INSERT INTO public.credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'commit', -p_amount, p_reservation_id || '-commit',
        jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'committed', 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;

CREATE OR REPLACE FUNCTION public.release_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_reservation public.credit_ledger%ROWTYPE;
    v_commit public.credit_ledger%ROWTYPE;
    v_release public.credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_reservation_id IS NULL OR btrim(p_reservation_id) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Do not acquire a shared reservation lock before this account lock.
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM public.credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;

    SELECT * INTO v_reservation FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id;
    IF NOT FOUND OR v_reservation.operation IS DISTINCT FROM 'reserve'
       OR v_reservation.user_id IS DISTINCT FROM p_user_id
       OR v_reservation.generation_id IS DISTINCT FROM p_generation_id
       OR v_reservation.amount IS DISTINCT FROM p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    SELECT * INTO v_commit FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id || '-commit';
    SELECT * INTO v_release FROM public.credit_ledger
    WHERE idempotency_key = p_reservation_id || '-release';

    IF v_commit.id IS NOT NULL AND (
        v_commit.operation IS DISTINCT FROM 'commit'
        OR v_commit.user_id IS DISTINCT FROM p_user_id
        OR v_commit.generation_id IS DISTINCT FROM p_generation_id
        OR v_commit.amount IS DISTINCT FROM -p_amount
    ) THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED'; END IF;
    IF v_release.id IS NOT NULL AND (
        v_release.operation IS DISTINCT FROM 'release'
        OR v_release.user_id IS DISTINCT FROM p_user_id
        OR v_release.generation_id IS DISTINCT FROM p_generation_id
        OR v_release.amount IS DISTINCT FROM p_amount
    ) THEN RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED'; END IF;
    IF v_commit.id IS NOT NULL AND v_release.id IS NOT NULL THEN
        -- Existing inconsistent history needs separate reconciliation, not silent repair.
        RAISE EXCEPTION 'CREDIT_RESERVATION_STATE_INVALID';
    END IF;

    IF v_release.id IS NOT NULL THEN
        RETURN jsonb_build_object('status', 'released', 'amount', p_amount);
    END IF;
    IF v_commit.id IS NOT NULL THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_ALREADY_COMMITTED';
    END IF;
    IF v_reserved < p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    UPDATE public.credit_accounts
    SET reserved = reserved - p_amount, updated_at = now()
    WHERE user_id = p_user_id;
    INSERT INTO public.credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'release', p_amount, p_reservation_id || '-release',
        jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'released', 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;

-- CREATE OR REPLACE preserves owner and existing permissions; explicitly preserve
-- the audited browser denial and backend access. No signature/return-type changes.
REVOKE ALL ON FUNCTION public.reserve_generation_credit(uuid, uuid, integer, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reserve_generation_credit(uuid, uuid, integer, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) TO service_role;
COMMIT;
