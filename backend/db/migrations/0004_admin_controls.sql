-- Admin controls (0004): disabled accounts, admin audit log, admin list
-- indexes and the atomic "grant generations" operation.
--
-- The migration runner wraps this file in a transaction, so it must not
-- contain BEGIN/COMMIT.

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

-- ---------------------------------------------------------------------
-- Disabled accounts
-- ---------------------------------------------------------------------

ALTER TABLE users ADD COLUMN disabled_at timestamptz NULL;

COMMENT ON COLUMN users.disabled_at IS
  'Set by an admin to block login and every authenticated request; NULL = active';

-- ---------------------------------------------------------------------
-- Admin audit log
-- ---------------------------------------------------------------------

CREATE TABLE admin_audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id uuid NULL REFERENCES users(id) ON DELETE SET NULL,
  admin_email text NOT NULL,
  action text NOT NULL,
  target_type text NOT NULL,
  target_id text NULL,
  details jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created
  ON admin_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_target
  ON admin_audit_log(target_type, target_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin_user
  ON admin_audit_log(admin_user_id);

COMMENT ON TABLE admin_audit_log IS 'One row per admin action (who, what, on which target)';

-- ---------------------------------------------------------------------
-- Indexes for the admin lists and dashboards
-- ---------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_brands_created_at ON brands(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_status_created
  ON generations(status, created_at DESC);
-- Also serves the ON DELETE SET NULL of generations.user_id when a user is deleted.
CREATE INDEX IF NOT EXISTS idx_generations_user_created
  ON generations(user_id, created_at DESC);
-- needs_review looks up the idempotency checkpoint of each generation.
CREATE INDEX IF NOT EXISTS idx_idempotency_records_generation
  ON idempotency_records(generation_id);
CREATE INDEX IF NOT EXISTS idx_generation_usage_created ON generation_usage(created_at);

-- ---------------------------------------------------------------------
-- Grant generations (admin)
--
-- Gives a user p_generations more generations in one transaction:
--   * credit_accounts.balance += p_credits, with a 'grant' ledger row;
--   * user_generation_quotas.generation_limit += p_generations.
-- Missing rows are created exactly as reserve_generation_credit and
-- reserve_generation_slot would create them (beta allowance / plan lifetime
-- limit) before the grant is added on top. Only balance and
-- generation_limit grow, so balance - reserved >= 0 and
-- consumed + reserved <= generation_limit keep holding, and open
-- reservations are untouched. The account row is locked first, like every
-- other credit writer (0003). The daily limit is not changed.
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION admin_grant_generations(
    p_user_id uuid,
    p_generations integer,
    p_credits integer,
    p_idempotency_key text,
    p_metadata jsonb
) RETURNS jsonb LANGUAGE plpgsql
AS $$
DECLARE
    v_lifetime_limit integer;
    v_balance integer;
    v_reserved integer;
    v_quota user_generation_quotas%ROWTYPE;
    v_ledger_id uuid;
BEGIN
    IF p_generations IS NULL OR p_generations <= 0 THEN
        RAISE EXCEPTION 'INVALID_GRANT_AMOUNT';
    END IF;
    IF p_credits IS NULL OR p_credits <= 0 THEN
        RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT';
    END IF;
    IF p_user_id IS NULL OR p_idempotency_key IS NULL OR btrim(p_idempotency_key) = '' THEN
        RAISE EXCEPTION 'INVALID_GRANT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM users WHERE id = p_user_id) THEN
        RAISE EXCEPTION 'USER_NOT_FOUND';
    END IF;

    -- Credits: same initial allowance as reserve_generation_credit.
    INSERT INTO credit_accounts(user_id, balance, reserved)
    VALUES (p_user_id, COALESCE((SELECT image_credits FROM plans WHERE code = 'beta'), 15), 0)
    ON CONFLICT (user_id) DO NOTHING;
    SELECT balance, reserved INTO v_balance, v_reserved
    FROM credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'CREDIT_ACCOUNT_NOT_FOUND'; END IF;

    UPDATE credit_accounts
    SET balance = balance + p_credits, updated_at = now()
    WHERE user_id = p_user_id
    RETURNING balance, reserved INTO v_balance, v_reserved;
    INSERT INTO credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (
        p_user_id, NULL, 'grant', p_credits, p_idempotency_key,
        COALESCE(p_metadata, '{}'::jsonb)
          || jsonb_build_object('generations', p_generations, 'credits', p_credits)
    )
    RETURNING id INTO v_ledger_id;

    -- Quota: same initial row as reserve_generation_slot.
    SELECT lifetime_image_limit INTO v_lifetime_limit
    FROM _plan_limits_for_user(p_user_id);
    INSERT INTO user_generation_quotas(user_id, generation_limit)
    VALUES (p_user_id, COALESCE(v_lifetime_limit, 42))
    ON CONFLICT (user_id) DO NOTHING;
    UPDATE user_generation_quotas
    SET generation_limit = generation_limit + p_generations, updated_at = now()
    WHERE user_id = p_user_id
    RETURNING * INTO v_quota;
    IF NOT FOUND THEN RAISE EXCEPTION 'GENERATION_QUOTA_NOT_FOUND'; END IF;

    RETURN jsonb_build_object(
        'user_id', p_user_id,
        'generations', p_generations,
        'credits', p_credits,
        'ledger_id', v_ledger_id,
        'idempotency_key', p_idempotency_key,
        'credit_balance', v_balance,
        'credit_reserved', v_reserved,
        'generation_limit', v_quota.generation_limit,
        'generation_reserved', v_quota.reserved,
        'generation_consumed', v_quota.consumed
    );
END;
$$;

COMMENT ON FUNCTION admin_grant_generations(uuid, integer, integer, text, jsonb) IS
  'Admin grant: raises the lifetime generation limit and the credit balance atomically';
