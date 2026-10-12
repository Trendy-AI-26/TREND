-- Free beta trial: 14 days from profile creation, three image generations per UTC day.
-- This is forward-only: it deliberately does not edit or replay earlier migrations.

ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS trial_started_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz NOT NULL DEFAULT (now() + interval '14 days');

UPDATE public.profiles
SET trial_started_at = COALESCE(trial_started_at, created_at, now()),
    trial_ends_at = COALESCE(trial_ends_at, COALESCE(trial_started_at, created_at, now()) + interval '14 days')
WHERE trial_started_at IS NULL OR trial_ends_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_profiles_trial_ends_at
    ON public.profiles(trial_ends_at);

-- Keep the existing lifetime accounting compatible, while enforcing the
-- product rule through the separate atomic daily usage table below.
UPDATE public.plans
SET image_credits = 42,
    lifetime_image_limit = 42
WHERE code = 'beta';

UPDATE public.user_generation_quotas
SET generation_limit = 42, updated_at = now()
WHERE generation_limit = 15;

UPDATE public.credit_accounts
SET balance = 42, updated_at = now()
WHERE balance = 15
  AND reserved = 0
  AND NOT EXISTS (
      SELECT 1 FROM public.credit_ledger cl WHERE cl.user_id = credit_accounts.user_id
  );

CREATE TABLE IF NOT EXISTS public.generation_daily_usage (
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    usage_date date NOT NULL,
    daily_limit integer NOT NULL DEFAULT 3,
    reserved integer NOT NULL DEFAULT 0,
    consumed integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, usage_date),
    CONSTRAINT generation_daily_usage_limit_positive CHECK (daily_limit >= 0),
    CONSTRAINT generation_daily_usage_reserved_non_negative CHECK (reserved >= 0),
    CONSTRAINT generation_daily_usage_consumed_non_negative CHECK (consumed >= 0),
    CONSTRAINT generation_daily_usage_not_over_limit CHECK (reserved + consumed <= daily_limit)
);

ALTER TABLE public.generation_quota_reservations
    ADD COLUMN IF NOT EXISTS usage_date date;
UPDATE public.generation_quota_reservations
SET usage_date = COALESCE(usage_date, (created_at AT TIME ZONE 'utc')::date)
WHERE usage_date IS NULL;
ALTER TABLE public.generation_quota_reservations
    ALTER COLUMN usage_date SET DEFAULT ((now() AT TIME ZONE 'utc')::date),
    ALTER COLUMN usage_date SET NOT NULL;

ALTER TABLE public.generation_daily_usage ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.reserve_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_lifetime_limit integer;
    v_quota public.user_generation_quotas%ROWTYPE;
    v_trial_ends_at timestamptz;
    v_usage public.generation_daily_usage%ROWTYPE;
    v_usage_date date := (now() AT TIME ZONE 'utc')::date;
BEGIN
    SELECT trial_ends_at INTO v_trial_ends_at
    FROM public.profiles
    WHERE user_id = p_user_id;
    IF v_trial_ends_at IS NULL OR now() >= v_trial_ends_at THEN
        RAISE EXCEPTION 'TRIAL_EXPIRED';
    END IF;

    SELECT lifetime_image_limit INTO v_lifetime_limit
    FROM public._plan_limits_for_user(p_user_id);
    INSERT INTO public.user_generation_quotas(user_id, generation_limit)
    VALUES (p_user_id, COALESCE(v_lifetime_limit, 42))
    ON CONFLICT (user_id) DO NOTHING;
    SELECT * INTO v_quota
    FROM public.user_generation_quotas
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF EXISTS (
        SELECT 1 FROM public.generation_quota_reservations
        WHERE generation_id = p_generation_id
    ) THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_EXISTS';
    END IF;
    IF v_quota.consumed + v_quota.reserved >= v_quota.generation_limit THEN
        RAISE EXCEPTION 'GENERATION_LIMIT_REACHED';
    END IF;

    INSERT INTO public.generation_daily_usage(user_id, usage_date, daily_limit)
    VALUES (p_user_id, v_usage_date, 3)
    ON CONFLICT (user_id, usage_date) DO NOTHING;
    SELECT * INTO v_usage
    FROM public.generation_daily_usage
    WHERE user_id = p_user_id AND usage_date = v_usage_date
    FOR UPDATE;
    IF v_usage.consumed + v_usage.reserved >= v_usage.daily_limit THEN
        RAISE EXCEPTION 'DAILY_GENERATION_LIMIT_REACHED';
    END IF;

    UPDATE public.user_generation_quotas
    SET reserved = reserved + 1, updated_at = now()
    WHERE user_id = p_user_id;
    UPDATE public.generation_daily_usage
    SET reserved = reserved + 1, updated_at = now()
    WHERE user_id = p_user_id AND usage_date = v_usage_date;
    INSERT INTO public.generation_quota_reservations(generation_id, user_id, usage_date)
    VALUES (p_generation_id, p_user_id, v_usage_date);
    RETURN jsonb_build_object(
        'generation_id', p_generation_id,
        'user_id', p_user_id,
        'status', 'reserved',
        'trial_ends_at', v_trial_ends_at,
        'daily_limit', v_usage.daily_limit,
        'daily_reserved', v_usage.reserved + 1,
        'daily_remaining', v_usage.daily_limit - v_usage.consumed - v_usage.reserved - 1
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_status text;
    v_usage_date date;
BEGIN
    SELECT status, usage_date INTO v_status, v_usage_date
    FROM public.generation_quota_reservations
    WHERE generation_id = p_generation_id AND user_id = p_user_id
    FOR UPDATE;
    IF v_status = 'committed' THEN
        RETURN jsonb_build_object('status', 'committed');
    END IF;
    IF v_status IS DISTINCT FROM 'reserved' THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.user_generation_quotas
    SET reserved = reserved - 1, consumed = consumed + 1, updated_at = now()
    WHERE user_id = p_user_id AND reserved > 0;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.generation_daily_usage
    SET reserved = reserved - 1, consumed = consumed + 1, updated_at = now()
    WHERE user_id = p_user_id AND usage_date = v_usage_date AND reserved > 0;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.generation_quota_reservations
    SET status = 'committed', completed_at = now()
    WHERE generation_id = p_generation_id;
    RETURN jsonb_build_object('status', 'committed');
END;
$$;

CREATE OR REPLACE FUNCTION public.release_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_status text;
    v_usage_date date;
BEGIN
    SELECT status, usage_date INTO v_status, v_usage_date
    FROM public.generation_quota_reservations
    WHERE generation_id = p_generation_id AND user_id = p_user_id
    FOR UPDATE;
    IF v_status = 'released' THEN
        RETURN jsonb_build_object('status', 'released');
    END IF;
    IF v_status IS DISTINCT FROM 'reserved' THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.user_generation_quotas
    SET reserved = reserved - 1, updated_at = now()
    WHERE user_id = p_user_id AND reserved > 0;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.generation_daily_usage
    SET reserved = reserved - 1, updated_at = now()
    WHERE user_id = p_user_id AND usage_date = v_usage_date AND reserved > 0;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'GENERATION_QUOTA_RESERVATION_NOT_FOUND';
    END IF;
    UPDATE public.generation_quota_reservations
    SET status = 'released', completed_at = now()
    WHERE generation_id = p_generation_id;
    RETURN jsonb_build_object('status', 'released');
END;
$$;

CREATE OR REPLACE FUNCTION public.get_generation_quota_summary(p_user_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_plan record;
    v_quota public.user_generation_quotas%ROWTYPE;
    v_daily public.generation_daily_usage%ROWTYPE;
    v_trial_ends_at timestamptz;
    v_today date := (now() AT TIME ZONE 'utc')::date;
    v_active_brands integer;
BEGIN
    SELECT * INTO v_plan FROM public._plan_limits_for_user(p_user_id);
    SELECT trial_ends_at INTO v_trial_ends_at FROM public.profiles WHERE user_id = p_user_id;
    INSERT INTO public.user_generation_quotas(user_id, generation_limit)
    VALUES (p_user_id, COALESCE(v_plan.lifetime_image_limit, 42))
    ON CONFLICT (user_id) DO NOTHING;
    INSERT INTO public.generation_daily_usage(user_id, usage_date, daily_limit)
    VALUES (p_user_id, v_today, 3)
    ON CONFLICT (user_id, usage_date) DO NOTHING;
    SELECT * INTO v_quota FROM public.user_generation_quotas WHERE user_id = p_user_id;
    SELECT * INTO v_daily FROM public.generation_daily_usage
    WHERE user_id = p_user_id AND usage_date = v_today;
    SELECT count(*) INTO v_active_brands FROM public.brands WHERE owner_user_id = p_user_id;
    RETURN jsonb_build_object(
        'plan', 'beta',
        'max_active_brands', v_plan.max_active_brands,
        'active_brands', v_active_brands,
        'generation_limit', v_quota.generation_limit,
        'generation_reserved', v_quota.reserved,
        'generation_consumed', v_quota.consumed,
        'generation_remaining', v_quota.generation_limit - v_quota.consumed - v_quota.reserved,
        'daily_generation_limit', v_daily.daily_limit,
        'daily_generation_reserved', v_daily.reserved,
        'daily_generation_consumed', v_daily.consumed,
        'daily_generation_remaining', v_daily.daily_limit - v_daily.consumed - v_daily.reserved,
        'trial_ends_at', v_trial_ends_at,
        'trial_active', v_trial_ends_at IS NOT NULL AND now() < v_trial_ends_at
    );
END;
$$;

CREATE OR REPLACE FUNCTION public.check_generation_rate_limit(
    p_user_id uuid,
    p_bucket text,
    p_limit integer,
    p_window_started_at timestamptz
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_count integer;
BEGIN
    IF p_limit <= 0 THEN RAISE EXCEPTION 'INVALID_RATE_LIMIT'; END IF;
    INSERT INTO public.rate_limit_buckets(user_id, bucket, window_started_at, request_count)
    VALUES (p_user_id, p_bucket, p_window_started_at, 1)
    ON CONFLICT (user_id, bucket, window_started_at)
    DO UPDATE SET request_count = public.rate_limit_buckets.request_count + 1
    WHERE public.rate_limit_buckets.request_count < p_limit
    RETURNING request_count INTO v_count;
    IF NOT FOUND THEN RAISE EXCEPTION 'RATE_LIMIT_EXCEEDED'; END IF;
    RETURN jsonb_build_object('accepted', true, 'request_count', v_count, 'limit', p_limit);
END;
$$;

-- Close the privilege gap in all service-only SECURITY DEFINER routines.
REVOKE ALL ON FUNCTION public.get_available_credits(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_generation_credit(uuid, uuid, integer, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public._plan_limits_for_user(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.create_brand_if_allowed(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.commit_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_generation_quota_summary(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.check_generation_rate_limit(uuid, text, integer, timestamptz) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.get_available_credits(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_generation_credit(uuid, uuid, integer, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public._plan_limits_for_user(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.create_brand_if_allowed(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_generation_quota_summary(uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.check_generation_rate_limit(uuid, text, integer, timestamptz) TO service_role;

-- Correct credit transitions: validate the active reservation and make retries no-ops.
CREATE OR REPLACE FUNCTION public.commit_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_balance integer; v_reserved integer; v_operation text; v_reserved_amount integer;
BEGIN
    IF p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF EXISTS (SELECT 1 FROM public.credit_ledger WHERE idempotency_key = p_reservation_id || '-commit') THEN
        RETURN jsonb_build_object('status', 'committed', 'amount', p_amount);
    END IF;
    SELECT operation, amount INTO v_operation, v_reserved_amount
    FROM public.credit_ledger
    WHERE user_id = p_user_id AND generation_id = p_generation_id AND idempotency_key = p_reservation_id
    FOR SHARE;
    IF v_operation IS NULL OR v_operation <> 'reserve' OR v_reserved_amount <> p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;
    IF EXISTS (SELECT 1 FROM public.credit_ledger WHERE idempotency_key = p_reservation_id || '-release') THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_ALREADY_RELEASED';
    END IF;
    SELECT balance, reserved INTO v_balance, v_reserved FROM public.credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND OR v_reserved < p_amount OR v_balance < p_amount THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;
    UPDATE public.credit_accounts SET balance = balance - p_amount, reserved = reserved - p_amount, updated_at = now() WHERE user_id = p_user_id;
    INSERT INTO public.credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'commit', -p_amount, p_reservation_id || '-commit', jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'committed', 'amount', p_amount);
END; $$;

CREATE OR REPLACE FUNCTION public.release_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_reserved integer; v_operation text; v_reserved_amount integer;
BEGIN
    IF p_amount <= 0 THEN RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT'; END IF;
    IF EXISTS (SELECT 1 FROM public.credit_ledger WHERE idempotency_key = p_reservation_id || '-release') THEN
        RETURN jsonb_build_object('status', 'released', 'amount', p_amount);
    END IF;
    SELECT operation, amount INTO v_operation, v_reserved_amount
    FROM public.credit_ledger
    WHERE user_id = p_user_id AND generation_id = p_generation_id AND idempotency_key = p_reservation_id
    FOR SHARE;
    IF v_operation IS NULL OR v_operation <> 'reserve' OR v_reserved_amount <> p_amount THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND';
    END IF;
    IF EXISTS (SELECT 1 FROM public.credit_ledger WHERE idempotency_key = p_reservation_id || '-commit') THEN
        RAISE EXCEPTION 'CREDIT_RESERVATION_ALREADY_COMMITTED';
    END IF;
    SELECT reserved INTO v_reserved FROM public.credit_accounts WHERE user_id = p_user_id FOR UPDATE;
    IF NOT FOUND OR v_reserved < p_amount THEN RAISE EXCEPTION 'CREDIT_RESERVATION_NOT_FOUND'; END IF;
    UPDATE public.credit_accounts SET reserved = reserved - p_amount, updated_at = now() WHERE user_id = p_user_id;
    INSERT INTO public.credit_ledger(user_id, generation_id, operation, amount, idempotency_key, metadata)
    VALUES (p_user_id, p_generation_id, 'release', p_amount, p_reservation_id || '-release', jsonb_build_object('amount', p_amount, 'reservation_id', p_reservation_id));
    RETURN jsonb_build_object('status', 'released', 'amount', p_amount);
END; $$;
REVOKE ALL ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.commit_generation_credit(uuid, uuid, text, integer) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_generation_credit(uuid, uuid, text, integer) TO service_role;
