-- Serialize credit reservation transitions (generation reliability, PR #82).
--
-- Account-first serialization: every credit writer (reserve / commit / release)
-- locks the user's credit_accounts row before it reads reservation or terminal
-- state, so concurrent transitions for one account queue instead of racing.
-- Independent users stay concurrent.
--
-- Behaviour changes versus 0001:
--   * reserve: a retry with the same key and the same user/generation/amount
--     replays the original receipt (even after completion) instead of raising
--     IDEMPOTENCY_KEY_REUSED. A mismatching retry still raises it.
--   * commit / release: matching retries are no-ops; a conflicting terminal
--     state, a mismatching receipt or an inconsistent ledger is rejected
--     without mutating anything.
--
-- Only function bodies are replaced. Names, signatures and return types are
-- unchanged, so app/services/credits.py keeps working as is. No data changes.
-- The migration runner wraps this file in a transaction.

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE OR REPLACE FUNCTION reserve_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_amount integer, p_idempotency_key text
) RETURNS jsonb LANGUAGE plpgsql
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_existing credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Preserve the existing initial-account allowance; never overwrite an account.
    INSERT INTO credit_accounts(user_id, balance, reserved)
    VALUES (p_user_id, COALESCE((SELECT image_credits FROM plans WHERE code = 'beta'), 15), 0)
    ON CONFLICT (user_id) DO NOTHING;
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_ACCOUNT_NOT_FOUND'; END IF;

    SELECT * INTO v_existing FROM credit_ledger
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
    UPDATE credit_accounts
    SET reserved = reserved + p_amount, updated_at = now() WHERE user_id = p_user_id;
    INSERT INTO credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'reserve', p_amount, p_idempotency_key,
        jsonb_build_object('amount', p_amount, 'generation_id', p_generation_id));
    RETURN jsonb_build_object('reservation_id', p_idempotency_key,
        'user_id', p_user_id, 'generation_id', p_generation_id, 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    -- Global key collision from another account: this block's mutations roll back.
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;

CREATE OR REPLACE FUNCTION commit_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_reservation credit_ledger%ROWTYPE;
    v_commit credit_ledger%ROWTYPE;
    v_release credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_reservation_id IS NULL OR btrim(p_reservation_id) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Do not acquire a shared reservation lock before this account lock.
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;

    SELECT * INTO v_reservation FROM credit_ledger
    WHERE idempotency_key = p_reservation_id;
    IF NOT FOUND OR v_reservation.operation IS DISTINCT FROM 'reserve'
       OR v_reservation.user_id IS DISTINCT FROM p_user_id
       OR v_reservation.generation_id IS DISTINCT FROM p_generation_id
       OR v_reservation.amount IS DISTINCT FROM p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    SELECT * INTO v_commit FROM credit_ledger
    WHERE idempotency_key = p_reservation_id || '-commit';
    SELECT * INTO v_release FROM credit_ledger
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

    UPDATE credit_accounts
    SET balance = balance - p_amount, reserved = reserved - p_amount, updated_at = now()
    WHERE user_id = p_user_id;
    INSERT INTO credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'commit', -p_amount, p_reservation_id || '-commit',
        jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'committed', 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;

CREATE OR REPLACE FUNCTION release_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_reservation credit_ledger%ROWTYPE;
    v_commit credit_ledger%ROWTYPE;
    v_release credit_ledger%ROWTYPE;
BEGIN
    IF p_amount IS NULL OR p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF p_user_id IS NULL OR p_generation_id IS NULL OR
       p_reservation_id IS NULL OR btrim(p_reservation_id) = '' THEN
        RAISE EXCEPTION 'INVALID_CREDIT_RESERVATION';
    END IF;

    -- Do not acquire a shared reservation lock before this account lock.
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;

    SELECT * INTO v_reservation FROM credit_ledger
    WHERE idempotency_key = p_reservation_id;
    IF NOT FOUND OR v_reservation.operation IS DISTINCT FROM 'reserve'
       OR v_reservation.user_id IS DISTINCT FROM p_user_id
       OR v_reservation.generation_id IS DISTINCT FROM p_generation_id
       OR v_reservation.amount IS DISTINCT FROM p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;

    SELECT * INTO v_commit FROM credit_ledger
    WHERE idempotency_key = p_reservation_id || '-commit';
    SELECT * INTO v_release FROM credit_ledger
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

    UPDATE credit_accounts
    SET reserved = reserved - p_amount, updated_at = now()
    WHERE user_id = p_user_id;
    INSERT INTO credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'release', p_amount, p_reservation_id || '-release',
        jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'released', 'amount', p_amount);
EXCEPTION WHEN unique_violation THEN
    RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
END;
$$;
