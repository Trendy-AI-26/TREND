CREATE TABLE IF NOT EXISTS public.trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,

    category TEXT,

    industry JSONB NOT NULL DEFAULT '[]'::jsonb,
    region JSONB NOT NULL DEFAULT '[]'::jsonb,
    platform JSONB NOT NULL DEFAULT '[]'::jsonb,
    audience JSONB NOT NULL DEFAULT '[]'::jsonb,

    visual_style JSONB NOT NULL DEFAULT '[]'::jsonb,
    content_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    avoid_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,

    popularity_score INTEGER NOT NULL DEFAULT 0,
    growth_score INTEGER NOT NULL DEFAULT 0,
    relevance_score INTEGER NOT NULL DEFAULT 0,

    status TEXT NOT NULL DEFAULT 'active',

    source TEXT,
    observed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT trends_status_check
        CHECK (status IN ('active', 'inactive', 'expired')),

    CONSTRAINT trends_popularity_score_check
        CHECK (popularity_score BETWEEN 0 AND 100),

    CONSTRAINT trends_growth_score_check
        CHECK (growth_score BETWEEN 0 AND 100),

    CONSTRAINT trends_relevance_score_check
        CHECK (relevance_score BETWEEN 0 AND 100)
);
