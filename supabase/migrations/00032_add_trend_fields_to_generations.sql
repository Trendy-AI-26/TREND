ALTER TABLE public.generations
    ADD COLUMN IF NOT EXISTS trend_id UUID
        REFERENCES public.trends(id)
        ON DELETE SET NULL,

    ADD COLUMN IF NOT EXISTS trend_snapshot JSONB,

    ADD COLUMN IF NOT EXISTS trend_applied BOOLEAN
        NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_generations_trend_id
    ON public.generations(trend_id);

COMMENT ON COLUMN public.generations.trend_id IS
    'The selected trend used for this generation, if any';

COMMENT ON COLUMN public.generations.trend_snapshot IS
    'Snapshot of the selected trend at generation time';

COMMENT ON COLUMN public.generations.trend_applied IS
    'Whether the selected trend was included in the final generation prompt';
