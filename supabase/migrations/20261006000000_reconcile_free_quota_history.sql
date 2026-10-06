-- The beta allowance is 15 images, including successful historical generations.
-- Failed generations do not consume the allowance. The old industry constraint
-- migration is already represented by 20261002081029.
UPDATE public.plans
SET image_credits = lifetime_image_limit
WHERE code = 'beta';

-- Serialize changes to these counters while initializing historical usage.
LOCK TABLE public.user_generation_quotas,
    public.generation_quota_reservations,
    public.credit_accounts IN SHARE ROW EXCLUSIVE MODE;

INSERT INTO public.user_generation_quotas(user_id, generation_limit)
SELECT DISTINCT b.owner_user_id, limits.lifetime_image_limit
FROM public.generations g
JOIN public.brands b ON b.id = g.brand_id
CROSS JOIN LATERAL public._plan_limits_for_user(b.owner_user_id) limits
WHERE g.status = 'succeeded'
ON CONFLICT (user_id) DO NOTHING;

-- Record historical successes once so retrying the backfill cannot double count.
WITH inserted AS (
    INSERT INTO public.generation_quota_reservations(
        generation_id, user_id, status, completed_at
    )
    SELECT g.id, b.owner_user_id, 'committed', g.created_at
    FROM public.generations g
    JOIN public.brands b ON b.id = g.brand_id
    WHERE g.status = 'succeeded'
    ON CONFLICT (generation_id) DO NOTHING
    RETURNING user_id
), counts AS (
    SELECT user_id, count(*)::integer AS used FROM inserted GROUP BY user_id
)
UPDATE public.user_generation_quotas q
SET consumed = LEAST(q.generation_limit - q.reserved, q.consumed + counts.used),
    updated_at = now()
FROM counts
WHERE q.user_id = counts.user_id;

-- Only initialize missing accounts; never overwrite existing credit balances.
INSERT INTO public.credit_accounts(user_id, balance, reserved)
SELECT user_id, GREATEST(generation_limit - consumed, 0), 0
FROM public.user_generation_quotas
ON CONFLICT (user_id) DO NOTHING;

NOTIFY pgrst, 'reload schema';
