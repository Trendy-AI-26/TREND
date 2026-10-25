-- =========================================================
-- Credits account
-- =========================================================

CREATE TABLE IF NOT EXISTS public.credit_accounts (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    balance INTEGER NOT NULL DEFAULT 0,
    reserved INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT credit_accounts_balance_non_negative
        CHECK (balance >= 0),

    CONSTRAINT credit_accounts_reserved_non_negative
        CHECK (reserved >= 0),

    CONSTRAINT credit_accounts_available_non_negative
        CHECK (balance - reserved >= 0)
);

-- =========================================================
-- Credit ledger
-- =========================================================

CREATE TABLE IF NOT EXISTS public.credit_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,

    generation_id UUID NULL
        REFERENCES public.generations(id) ON DELETE SET NULL,

    operation TEXT NOT NULL,

    amount INTEGER NOT NULL,

    idempotency_key TEXT NOT NULL UNIQUE,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT credit_ledger_operation_check
        CHECK (
            operation IN (
                'grant',
                'reserve',
                'commit',
                'release',
                'refund',
                'adjustment'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_created
    ON public.credit_ledger(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_credit_ledger_generation
    ON public.credit_ledger(generation_id);

-- =========================================================
-- Usage events
-- =========================================================

CREATE TABLE IF NOT EXISTS public.usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,

    generation_id UUID NULL
        REFERENCES public.generations(id) ON DELETE SET NULL,

    feature TEXT NOT NULL,

    provider TEXT NOT NULL,

    model TEXT NOT NULL,

    status TEXT NOT NULL,

    units INTEGER NOT NULL DEFAULT 1,

    credits INTEGER NOT NULL DEFAULT 0,

    duration_ms INTEGER NULL,

    request_id TEXT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT usage_events_status_check
        CHECK (
            status IN (
                'started',
                'succeeded',
                'failed'
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_created
    ON public.usage_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_feature_created
    ON public.usage_events(feature, created_at DESC);

-- =========================================================
-- Idempotency records
-- =========================================================

CREATE TABLE IF NOT EXISTS public.idempotency_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,

    scope TEXT NOT NULL,

    idempotency_key TEXT NOT NULL,

    request_hash TEXT NOT NULL,

    generation_id UUID NULL
        REFERENCES public.generations(id) ON DELETE SET NULL,

    status TEXT NOT NULL DEFAULT 'processing',

    response_status INTEGER NULL,

    response_body JSONB NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    completed_at TIMESTAMPTZ NULL,

    UNIQUE(user_id, scope, idempotency_key),

    CONSTRAINT idempotency_status_check
        CHECK (
            status IN (
                'processing',
                'succeeded',
                'failed'
            )
        )
);

-- =========================================================
-- Active generation locks
-- =========================================================

CREATE TABLE IF NOT EXISTS public.generation_locks (
    user_id UUID PRIMARY KEY
        REFERENCES auth.users(id) ON DELETE CASCADE,

    generation_id UUID NOT NULL
        REFERENCES public.generations(id) ON DELETE CASCADE,

    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generation_locks_expires
    ON public.generation_locks(expires_at);

-- =========================================================
-- Rate limit buckets
-- =========================================================

CREATE TABLE IF NOT EXISTS public.rate_limit_buckets (
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,

    bucket TEXT NOT NULL,

    window_started_at TIMESTAMPTZ NOT NULL,

    request_count INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY(user_id, bucket, window_started_at)
);

-- =========================================================
-- Generation columns
-- =========================================================

ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS user_id UUID
        REFERENCES auth.users(id) ON DELETE SET NULL;

ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS credits_reserved INTEGER
        NOT NULL DEFAULT 0;

ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS credits_charged INTEGER
        NOT NULL DEFAULT 0;

ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS product_asset_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS uq_generations_user_idempotency
    ON public.generations(user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

ALTER TABLE public.usage_events
    ADD COLUMN IF NOT EXISTS provider_request_id text;

-- These tables are accessed by the backend service-role client only. With RLS
-- enabled and no browser-role policies, anon/authenticated clients cannot
-- inspect or alter balances, reservations, usage, locks, or rate-limit state.
ALTER TABLE public.credit_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.idempotency_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generation_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limit_buckets ENABLE ROW LEVEL SECURITY;
