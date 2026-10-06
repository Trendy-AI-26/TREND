-- Free-plan limits are plan data, not application constants.
ALTER TABLE public.plans
    ADD COLUMN IF NOT EXISTS max_active_brands integer NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS lifetime_image_limit integer NOT NULL DEFAULT 15;

UPDATE public.plans
SET max_active_brands = 3,
    lifetime_image_limit = 15
WHERE code = 'beta';

CREATE TABLE IF NOT EXISTS public.user_generation_quotas (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    generation_limit integer NOT NULL,
    reserved integer NOT NULL DEFAULT 0,
    consumed integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT user_generation_quotas_limit_positive CHECK (generation_limit >= 0),
    CONSTRAINT user_generation_quotas_reserved_non_negative CHECK (reserved >= 0),
    CONSTRAINT user_generation_quotas_consumed_non_negative CHECK (consumed >= 0),
    CONSTRAINT user_generation_quotas_not_over_limit
        CHECK (consumed + reserved <= generation_limit)
);

CREATE TABLE IF NOT EXISTS public.generation_quota_reservations (
    generation_id uuid PRIMARY KEY REFERENCES public.generations(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'reserved',
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CONSTRAINT generation_quota_reservation_status_check
        CHECK (status IN ('reserved', 'committed', 'released'))
);

CREATE INDEX IF NOT EXISTS idx_generation_quota_reservations_user
    ON public.generation_quota_reservations(user_id, status);

ALTER TABLE public.user_generation_quotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_quota_reservations ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public._plan_limits_for_user(p_user_id uuid)
RETURNS TABLE(max_active_brands integer, lifetime_image_limit integer)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        COALESCE(active_plan.max_active_brands, beta.max_active_brands, 3),
        COALESCE(active_plan.lifetime_image_limit, beta.lifetime_image_limit, 15)
    FROM (SELECT 1) AS marker
    LEFT JOIN LATERAL (
        SELECT p.max_active_brands, p.lifetime_image_limit
        FROM public.subscriptions s
        JOIN public.plans p ON p.id = s.plan_id
        WHERE s.user_id = p_user_id
          AND s.status = 'active'
          AND s.period_end > now()
          AND p.is_active
        ORDER BY s.created_at DESC
        LIMIT 1
    ) AS active_plan ON true
    LEFT JOIN LATERAL (
        SELECT p.max_active_brands, p.lifetime_image_limit
        FROM public.plans p
        WHERE p.code = 'beta' AND p.is_active
        LIMIT 1
    ) AS beta ON true;
$$;

CREATE OR REPLACE FUNCTION public.create_brand_if_allowed(
    p_user_id uuid,
    p_name text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_limit integer;
    v_count integer;
    v_brand public.brands%ROWTYPE;
BEGIN
    SELECT max_active_brands INTO v_limit
    FROM public._plan_limits_for_user(p_user_id);

    -- Serialize brand creation per user so concurrent requests cannot exceed 3.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_user_id::text, 29001));

    SELECT count(*) INTO v_count
    FROM public.brands
    WHERE owner_user_id = p_user_id;

    IF v_count >= v_limit THEN
        RAISE EXCEPTION 'BRAND_LIMIT_REACHED';
    END IF;

    INSERT INTO public.brands(owner_user_id, name)
    VALUES (p_user_id, trim(p_name))
    RETURNING * INTO v_brand;

    RETURN jsonb_build_object(
        'id', v_brand.id,
        'owner_user_id', v_brand.owner_user_id,
        'name', v_brand.name,
        'logo_path', v_brand.logo_path,
        'created_at', v_brand.created_at,
        'updated_at', v_brand.updated_at
    );
EXCEPTION
    WHEN unique_violation THEN
        RAISE EXCEPTION 'DUPLICATE_BRAND_NAME';
END;
$$;

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
    v_limit integer;
    v_quota public.user_generation_quotas%ROWTYPE;
BEGIN
    SELECT lifetime_image_limit INTO v_limit
    FROM public._plan_limits_for_user(p_user_id);

    INSERT INTO public.user_generation_quotas(user_id, generation_limit)
    VALUES (p_user_id, v_limit)
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

    UPDATE public.user_generation_quotas
    SET reserved = reserved + 1, updated_at = now()
    WHERE user_id = p_user_id;

    INSERT INTO public.generation_quota_reservations(generation_id, user_id)
    VALUES (p_generation_id, p_user_id);

    RETURN jsonb_build_object(
        'generation_id', p_generation_id,
        'user_id', p_user_id,
        'status', 'reserved'
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
BEGIN
    SELECT status INTO v_status
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
BEGIN
    SELECT status INTO v_status
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
    v_active_brands integer;
BEGIN
    SELECT * INTO v_plan FROM public._plan_limits_for_user(p_user_id);

    INSERT INTO public.user_generation_quotas(user_id, generation_limit)
    VALUES (p_user_id, v_plan.lifetime_image_limit)
    ON CONFLICT (user_id) DO NOTHING;

    SELECT * INTO v_quota
    FROM public.user_generation_quotas
    WHERE user_id = p_user_id;

    SELECT count(*) INTO v_active_brands
    FROM public.brands WHERE owner_user_id = p_user_id;

    RETURN jsonb_build_object(
        'plan', 'beta',
        'max_active_brands', v_plan.max_active_brands,
        'active_brands', v_active_brands,
        'generation_limit', v_quota.generation_limit,
        'generation_reserved', v_quota.reserved,
        'generation_consumed', v_quota.consumed,
        'generation_remaining', v_quota.generation_limit - v_quota.consumed - v_quota.reserved
    );
END;
$$;

REVOKE ALL ON FUNCTION public._plan_limits_for_user(uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.create_brand_if_allowed(uuid, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.reserve_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.commit_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.release_generation_slot(uuid, uuid) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.get_generation_quota_summary(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.create_brand_if_allowed(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.reserve_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.release_generation_slot(uuid, uuid) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_generation_quota_summary(uuid) TO service_role;

-- Keep the existing credit ledger compatible with the free quota. New free
-- accounts start with the plan's 15 image credits instead of zero credits.
CREATE OR REPLACE FUNCTION public.reserve_generation_credit(
    p_user_id uuid,
    p_generation_id uuid,
    p_amount integer,
    p_idempotency_key text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
    v_available integer;
    v_existing_id uuid;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'INVALID_CREDIT_AMOUNT';
    END IF;

    SELECT id INTO v_existing_id
    FROM public.credit_ledger
    WHERE user_id = p_user_id AND idempotency_key = p_idempotency_key
    LIMIT 1;
    IF v_existing_id IS NOT NULL THEN
        RAISE EXCEPTION 'IDEMPOTENCY_KEY_REUSED';
    END IF;

    INSERT INTO public.credit_accounts(user_id, balance, reserved)
    VALUES (
        p_user_id,
        COALESCE((SELECT image_credits FROM public.plans WHERE code = 'beta'), 15),
        0
    )
    ON CONFLICT (user_id) DO NOTHING;

    SELECT balance, reserved INTO v_balance, v_reserved
    FROM public.credit_accounts
    WHERE user_id = p_user_id
    FOR UPDATE;

    v_available := greatest(coalesce(v_balance, 0) - coalesce(v_reserved, 0), 0);
    IF v_available < p_amount THEN
        RAISE EXCEPTION 'INSUFFICIENT_CREDITS';
    END IF;

    UPDATE public.credit_accounts
    SET reserved = reserved + p_amount, updated_at = now()
    WHERE user_id = p_user_id;

    INSERT INTO public.credit_ledger(
        user_id, generation_id, operation, amount, idempotency_key, metadata
    )
    VALUES (
        p_user_id, p_generation_id, 'reserve', p_amount, p_idempotency_key,
        jsonb_build_object('amount', p_amount, 'generation_id', p_generation_id)
    );

    RETURN jsonb_build_object(
        'reservation_id', p_idempotency_key,
        'user_id', p_user_id,
        'generation_id', p_generation_id,
        'amount', p_amount
    );
END;
$$;

GRANT EXECUTE ON FUNCTION public.reserve_generation_credit(uuid, uuid, integer, text)
    TO service_role;

-- Accounts created by the previous migration with no ledger activity were only
-- placeholders. Give those untouched beta accounts the new free allowance.
UPDATE public.credit_accounts ca
SET balance = COALESCE((SELECT image_credits FROM public.plans WHERE code = 'beta'), 15),
    updated_at = now()
WHERE ca.balance = 0
  AND ca.reserved = 0
  AND NOT EXISTS (
      SELECT 1 FROM public.credit_ledger cl WHERE cl.user_id = ca.user_id
  );
