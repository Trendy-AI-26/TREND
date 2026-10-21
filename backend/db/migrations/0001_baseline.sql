-- =====================================================================
-- TRENDY AI - plain PostgreSQL baseline (0001)
--
-- Equals the FINAL state produced by the old Supabase migrations in
-- supabase/migrations/ (00001 ... 20261006000000), with every
-- Supabase-specific object removed:
--   * no auth.users / auth.uid()  -> app-owned users table
--   * no RLS policies             -> ownership is enforced by the backend
--   * no anon/authenticated/service_role grants
--   * no storage.* (buckets live in S3/MinIO) and no vault.* (provider keys
--     are Fernet-encrypted by the backend and stored in provider_keys)
--   * no NOTIFY pgrst
--
-- The runner (python -m app.db.migrate) wraps this file in a transaction,
-- so it must not contain BEGIN/COMMIT.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------

CREATE TYPE provider_t AS ENUM ('openai', 'gemini');

CREATE TYPE tone_t AS ENUM ('formal', 'casual', 'playful', 'professional', 'friendly');

CREATE TYPE logo_mode_t AS ENUM ('none', 'prompt', 'watermark', 'both');

CREATE TYPE kit_status_t AS ENUM ('not_started', 'in_progress', 'complete');

CREATE TYPE generation_status_t AS ENUM ('pending', 'processing', 'succeeded', 'failed');

-- NOTE: the old migrations only defined the first 13 values minus
-- instagram_reel_cover / facebook_cover / tiktok_video_cover (they listed
-- tiktok_video), while the application (app/services/presets.py) generates
-- those three presets. They are included here so a fresh database accepts
-- every preset the API can produce. 'tiktok_video' is kept for compatibility.
CREATE TYPE platform_preset_t AS ENUM (
  'instagram_post',
  'instagram_story',
  'instagram_reel_cover',
  'facebook_post',
  'facebook_cover',
  'facebook_story',
  'twitter_post',
  'twitter_header',
  'linkedin_post',
  'linkedin_banner',
  'pinterest_pin',
  'tiktok_video',
  'tiktok_video_cover',
  'youtube_thumbnail',
  'youtube_banner',
  'snapchat_story'
);

-- ---------------------------------------------------------------------
-- Helper functions
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION all_hex_colors(TEXT[])
RETURNS BOOLEAN AS $$
BEGIN
  RETURN NOT EXISTS (
    SELECT 1
    FROM unnest($1) AS color
    WHERE color !~ '^#[0-9A-Fa-f]{6}$'
  );
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- ---------------------------------------------------------------------
-- Auth: users and one-time codes (replace Supabase auth.users)
-- ---------------------------------------------------------------------

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  email_verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Case-insensitive unique email.
CREATE UNIQUE INDEX uq_users_email_ci ON users (lower(email));

CREATE TRIGGER trigger_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE users IS 'Application-owned accounts (email + bcrypt password hash)';

CREATE TABLE auth_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_auth_codes_purpose
    CHECK (purpose IN ('verify_email', 'reset_password')),
  CONSTRAINT chk_auth_codes_attempts_non_negative CHECK (attempts >= 0)
);

CREATE INDEX idx_auth_codes_user_purpose_created
  ON auth_codes(user_id, purpose, created_at DESC);

COMMENT ON TABLE auth_codes IS 'Hashed 6-digit email codes (verify email / reset password)';

-- ---------------------------------------------------------------------
-- Profiles
-- ---------------------------------------------------------------------

CREATE TABLE profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  full_name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  avatar_path TEXT,
  trial_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  trial_ends_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '14 days'),
  CONSTRAINT chk_profiles_full_name_length
    CHECK (full_name IS NULL OR (LENGTH(TRIM(full_name)) >= 2 AND LENGTH(TRIM(full_name)) <= 120)),
  CONSTRAINT chk_profiles_avatar_url_format
    CHECK (avatar_url IS NULL OR avatar_url ~ '^https?://.+'),
  CONSTRAINT chk_profiles_avatar_path_format
    CHECK (avatar_path IS NULL OR avatar_path ~ '^avatars/[0-9a-f-]+/avatar\.(png|jpg|webp)$')
);

CREATE INDEX idx_profiles_trial_ends_at ON profiles(trial_ends_at);

CREATE TRIGGER trigger_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE profiles IS 'User profile information - one-to-one with users';
COMMENT ON COLUMN profiles.user_id IS 'User ID from users';
COMMENT ON COLUMN profiles.full_name IS 'User display name (2-120 characters when provided)';
COMMENT ON COLUMN profiles.avatar_url IS 'URL to user avatar image (must be valid HTTP/HTTPS URL)';
COMMENT ON COLUMN profiles.avatar_path IS 'Object storage path for the user avatar';

-- Create the profile row when a user signs up (replaces the auth.users trigger).
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO profiles (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_user_created
  AFTER INSERT ON users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

COMMENT ON FUNCTION handle_new_user() IS 'Auto-creates the profile row when a new user is inserted';

-- ---------------------------------------------------------------------
-- Brands
-- ---------------------------------------------------------------------

CREATE TABLE brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  logo_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_brands_name_length
    CHECK (LENGTH(TRIM(name)) >= 2 AND LENGTH(TRIM(name)) <= 120),
  CONSTRAINT chk_brands_logo_path_format
    CHECK (logo_path IS NULL OR logo_path ~ '^brands/[0-9a-f-]+/logo\.[A-Za-z0-9]+$')
);

CREATE UNIQUE INDEX uq_brands_owner_name_ci ON brands(owner_user_id, lower(name));
CREATE INDEX idx_brands_owner_created ON brands(owner_user_id, created_at DESC);

CREATE TRIGGER trigger_brands_updated_at
  BEFORE UPDATE ON brands
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE brands IS 'Business brands owned by users';
COMMENT ON COLUMN brands.owner_user_id IS 'User who owns this brand';
COMMENT ON COLUMN brands.name IS 'Brand display name (2-120 characters)';
COMMENT ON COLUMN brands.logo_path IS 'Object storage path for brand logo';

-- ---------------------------------------------------------------------
-- Product assets (before brand_kits / generations, which reference it)
-- ---------------------------------------------------------------------

CREATE TABLE product_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,
  CONSTRAINT chk_product_assets_storage_path
    CHECK (storage_path ~ '^brands/[0-9a-f-]+/product-assets/[0-9a-f-]+\.(png|jpg|webp)$'),
  CONSTRAINT chk_product_assets_content_type
    CHECK (content_type IN ('image/png', 'image/jpeg', 'image/webp')),
  CONSTRAINT chk_product_assets_file_size
    CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760),
  CONSTRAINT chk_product_assets_dimensions
    CHECK (width > 0 AND width <= 8192 AND height > 0 AND height <= 8192)
);

CREATE INDEX idx_product_assets_brand_created ON product_assets(brand_id, created_at DESC);
CREATE INDEX idx_product_assets_owner ON product_assets(owner_user_id);

COMMENT ON TABLE product_assets IS 'Optional product reference images used during generation';
COMMENT ON COLUMN product_assets.storage_path IS 'Private object storage path for the product image';
COMMENT ON COLUMN product_assets.owner_user_id IS 'User who uploaded the product image';

-- ---------------------------------------------------------------------
-- Brand kits
-- ---------------------------------------------------------------------

CREATE TABLE brand_kits (
  brand_id UUID PRIMARY KEY REFERENCES brands(id) ON DELETE CASCADE,
  tagline TEXT,
  tone tone_t,
  audience TEXT,
  colors TEXT[] NOT NULL DEFAULT '{}',
  avoid_words TEXT,
  summary TEXT,
  status kit_status_t NOT NULL DEFAULT 'not_started',
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  industry TEXT,
  product_asset_id UUID REFERENCES product_assets(id) ON DELETE SET NULL,
  CONSTRAINT chk_brand_kits_tagline_length
    CHECK (tagline IS NULL OR LENGTH(TRIM(tagline)) <= 160),
  CONSTRAINT chk_brand_kits_audience_length
    CHECK (audience IS NULL OR (LENGTH(TRIM(audience)) >= 2 AND LENGTH(TRIM(audience)) <= 500)),
  CONSTRAINT chk_brand_kits_colors_count
    CHECK (cardinality(colors) <= 3),
  CONSTRAINT chk_brand_kits_colors_format
    CHECK (all_hex_colors(colors)),
  CONSTRAINT chk_brand_kits_status_complete_consistency
    CHECK (
      (status = 'complete' AND tone IS NOT NULL AND audience IS NOT NULL AND cardinality(colors) >= 1)
      OR
      (status != 'complete')
    ),
  CONSTRAINT chk_brand_kits_completed_at_consistency
    CHECK (
      (status = 'complete' AND completed_at IS NOT NULL)
      OR
      (status != 'complete' AND completed_at IS NULL)
    ),
  CONSTRAINT chk_brand_kits_industry_length
    CHECK (industry IS NULL OR LENGTH(TRIM(industry)) <= 120),
  -- Originally added NOT VALID to preserve legacy rows; the database starts
  -- empty here so it is simply enforced.
  CONSTRAINT chk_brand_kits_complete_requires_industry
    CHECK (
      status <> 'complete'
      OR (
        NULLIF(BTRIM(industry), '') IS NOT NULL
        AND NULLIF(BTRIM(audience), '') IS NOT NULL
        AND COALESCE(cardinality(colors), 0) >= 1
      )
    )
);

CREATE TRIGGER trigger_brand_kits_updated_at
  BEFORE UPDATE ON brand_kits
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE brand_kits IS 'Brand identity questionnaire answers - one-to-one with brands';
COMMENT ON COLUMN brand_kits.colors IS 'Brand colors (array of hex codes, max 3)';
COMMENT ON COLUMN brand_kits.industry IS 'Brand industry or business category';
COMMENT ON COLUMN brand_kits.product_asset_id IS 'Product image selected during brand identity setup';
COMMENT ON CONSTRAINT chk_brand_kits_complete_requires_industry ON brand_kits IS
  'Completed kits require a non-empty industry, audience, and at least one color.';

-- ---------------------------------------------------------------------
-- Provider keys (BYOK). The key is Fernet-encrypted by the backend
-- (APP_ENCRYPTION_KEY); this replaces provider_keys.vault_secret_id.
-- ---------------------------------------------------------------------

CREATE TABLE provider_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  provider provider_t NOT NULL,
  encrypted_key TEXT NOT NULL,
  label TEXT,
  key_hint TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_valid BOOLEAN,
  last_validated_at TIMESTAMPTZ,
  last_validation_error TEXT,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_provider_keys_label_length
    CHECK (label IS NULL OR LENGTH(TRIM(label)) <= 100),
  CONSTRAINT chk_provider_keys_key_hint_format
    CHECK (key_hint IS NULL OR key_hint ~ '^[A-Za-z0-9_-]{2,16}$')
);

CREATE UNIQUE INDEX uq_provider_keys_one_active ON provider_keys(brand_id, provider) WHERE is_active;
CREATE INDEX idx_provider_keys_lookup ON provider_keys(brand_id, provider, created_at DESC);

CREATE TRIGGER trigger_provider_keys_updated_at
  BEFORE UPDATE ON provider_keys
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE provider_keys IS 'API key metadata for image generation providers';
COMMENT ON COLUMN provider_keys.encrypted_key IS 'Fernet-encrypted provider API key (APP_ENCRYPTION_KEY)';
COMMENT ON COLUMN provider_keys.key_hint IS 'Last N chars of key for display (2-16 chars)';

-- ---------------------------------------------------------------------
-- Trends (before generations, which reference it)
-- ---------------------------------------------------------------------

CREATE TABLE trends (
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
  CONSTRAINT trends_status_check CHECK (status IN ('active', 'inactive', 'expired')),
  CONSTRAINT trends_popularity_score_check CHECK (popularity_score BETWEEN 0 AND 100),
  CONSTRAINT trends_growth_score_check CHECK (growth_score BETWEEN 0 AND 100),
  CONSTRAINT trends_relevance_score_check CHECK (relevance_score BETWEEN 0 AND 100)
);

-- ---------------------------------------------------------------------
-- Generations
-- ---------------------------------------------------------------------

CREATE TABLE generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  prompt TEXT NOT NULL,
  provider provider_t NOT NULL,
  model TEXT NOT NULL,
  platform_preset platform_preset_t NOT NULL,
  width INT NOT NULL,
  height INT NOT NULL,
  logo_mode logo_mode_t NOT NULL DEFAULT 'none',
  status generation_status_t NOT NULL DEFAULT 'pending',
  provider_request_id TEXT,
  image_path TEXT,
  error_code TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  language TEXT NOT NULL DEFAULT 'ar',
  brief JSONB,
  product_asset_id UUID REFERENCES product_assets(id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  idempotency_key TEXT,
  credits_reserved INTEGER NOT NULL DEFAULT 0,
  credits_charged INTEGER NOT NULL DEFAULT 0,
  trend_id UUID REFERENCES trends(id) ON DELETE SET NULL,
  trend_snapshot JSONB,
  trend_applied BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT chk_generations_prompt_length
    CHECK (LENGTH(TRIM(prompt)) >= 3 AND LENGTH(TRIM(prompt)) <= 4000),
  CONSTRAINT chk_generations_model_length
    CHECK (LENGTH(TRIM(model)) >= 3 AND LENGTH(TRIM(model)) <= 100),
  CONSTRAINT chk_generations_dimensions
    CHECK (width >= 256 AND width <= 4096 AND height >= 256 AND height <= 4096),
  CONSTRAINT chk_generations_image_path_format
    CHECK (image_path IS NULL OR image_path ~ '^brands/[0-9a-f-]+/generations/[0-9a-f-]+\.png$'),
  CONSTRAINT chk_generations_status_succeeded
    CHECK (
      status != 'succeeded' OR (
        image_path IS NOT NULL AND
        error_code IS NULL AND
        error_message IS NULL AND
        completed_at IS NOT NULL
      )
    ),
  CONSTRAINT chk_generations_status_failed
    CHECK (
      status != 'failed' OR (
        image_path IS NULL AND
        error_code IS NOT NULL AND
        completed_at IS NOT NULL
      )
    ),
  CONSTRAINT chk_generations_status_pending_processing
    CHECK (
      status NOT IN ('pending', 'processing') OR (
        image_path IS NULL AND
        error_code IS NULL AND
        error_message IS NULL AND
        completed_at IS NULL
      )
    ),
  CONSTRAINT chk_generations_language CHECK (language IN ('ar', 'en'))
);

CREATE INDEX idx_generations_brand_created ON generations(brand_id, created_at DESC);
CREATE INDEX idx_generations_brand_status_created ON generations(brand_id, status, created_at DESC);
CREATE INDEX idx_generations_brand_provider_created ON generations(brand_id, provider, created_at DESC);
CREATE INDEX idx_generations_product_asset ON generations(product_asset_id);
CREATE INDEX idx_generations_trend_id ON generations(trend_id);
CREATE UNIQUE INDEX uq_generations_user_idempotency
  ON generations(user_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE TRIGGER trigger_generations_updated_at
  BEFORE UPDATE ON generations
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE generations IS 'Image generation requests and outcomes';
COMMENT ON COLUMN generations.image_path IS 'Object storage path to generated image';
COMMENT ON COLUMN generations.language IS 'Text language selected for the generation: ar or en';
COMMENT ON COLUMN generations.brief IS
  'Snapshot of the structured generation questionnaire used for downstream caption generation';
COMMENT ON COLUMN generations.product_asset_id IS
  'Optional product reference image used for this generation';
COMMENT ON COLUMN generations.trend_id IS 'The selected trend used for this generation, if any';
COMMENT ON COLUMN generations.trend_snapshot IS 'Snapshot of the selected trend at generation time';
COMMENT ON COLUMN generations.trend_applied IS
  'Whether the selected trend was included in the final generation prompt';

-- ---------------------------------------------------------------------
-- Plans and subscriptions
-- ---------------------------------------------------------------------

CREATE TABLE plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  image_credits INTEGER NOT NULL CHECK (image_credits >= 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  max_active_brands INTEGER NOT NULL DEFAULT 3,
  lifetime_image_limit INTEGER NOT NULL DEFAULT 15
);

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES plans(id),
  status TEXT NOT NULL DEFAULT 'active',
  period_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  period_end TIMESTAMPTZ NOT NULL,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX subscriptions_one_active_per_user
  ON subscriptions(user_id)
  WHERE status = 'active';

-- Seed: the free beta plan with its final values (42 images, 3 active brands).
INSERT INTO plans (code, name, image_credits, max_active_brands, lifetime_image_limit)
VALUES ('beta', 'Beta', 42, 3, 42)
ON CONFLICT (code) DO NOTHING;

-- ---------------------------------------------------------------------
-- Credits, usage, idempotency, locks, rate limits, quotas
-- ---------------------------------------------------------------------

CREATE TABLE credit_accounts (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0,
  reserved INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT credit_accounts_balance_non_negative CHECK (balance >= 0),
  CONSTRAINT credit_accounts_reserved_non_negative CHECK (reserved >= 0),
  CONSTRAINT credit_accounts_available_non_negative CHECK (balance - reserved >= 0)
);

CREATE TABLE credit_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  generation_id UUID NULL REFERENCES generations(id) ON DELETE SET NULL,
  operation TEXT NOT NULL,
  amount INTEGER NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT credit_ledger_operation_check
    CHECK (operation IN ('grant', 'reserve', 'commit', 'release', 'refund', 'adjustment'))
);

CREATE INDEX idx_credit_ledger_user_created ON credit_ledger(user_id, created_at DESC);
CREATE INDEX idx_credit_ledger_generation ON credit_ledger(generation_id);

CREATE TABLE usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  generation_id UUID NULL REFERENCES generations(id) ON DELETE SET NULL,
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
  provider_request_id TEXT,
  CONSTRAINT usage_events_status_check
    CHECK (status IN ('started', 'succeeded', 'failed'))
);

CREATE INDEX idx_usage_events_user_created ON usage_events(user_id, created_at DESC);
CREATE INDEX idx_usage_events_feature_created ON usage_events(feature, created_at DESC);

CREATE TABLE idempotency_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scope TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  generation_id UUID NULL REFERENCES generations(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'processing',
  response_status INTEGER NULL,
  response_body JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  UNIQUE (user_id, scope, idempotency_key),
  CONSTRAINT idempotency_status_check
    CHECK (status IN ('processing', 'succeeded', 'failed'))
);

-- NOTE: the old migration declared generation_id REFERENCES generations(id),
-- but the API acquires this lock BEFORE it inserts the generation row, which
-- would make every lock insert fail. The FK is therefore omitted; the lock is
-- keyed by user and generation_id is informational (used by the release).
CREATE TABLE generation_locks (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  generation_id UUID NOT NULL,
  acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_generation_locks_expires ON generation_locks(expires_at);

CREATE TABLE rate_limit_buckets (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  bucket TEXT NOT NULL,
  window_started_at TIMESTAMPTZ NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, bucket, window_started_at)
);

CREATE TABLE generation_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  generation_id UUID REFERENCES generations(id) ON DELETE SET NULL,
  operation TEXT NOT NULL,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  status TEXT NOT NULL,
  credits_charged INTEGER NOT NULL DEFAULT 0,
  estimated_provider_cost NUMERIC(12, 6),
  provider_request_id TEXT,
  error_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE generation_captions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  generation_id UUID NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  language TEXT NOT NULL,
  platform TEXT NOT NULL,
  caption_text TEXT NOT NULL,
  hashtags JSONB NOT NULL DEFAULT '[]'::jsonb,
  keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_generation_quotas (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  generation_limit INTEGER NOT NULL,
  reserved INTEGER NOT NULL DEFAULT 0,
  consumed INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT user_generation_quotas_limit_positive CHECK (generation_limit >= 0),
  CONSTRAINT user_generation_quotas_reserved_non_negative CHECK (reserved >= 0),
  CONSTRAINT user_generation_quotas_consumed_non_negative CHECK (consumed >= 0),
  CONSTRAINT user_generation_quotas_not_over_limit
    CHECK (consumed + reserved <= generation_limit)
);

CREATE TABLE generation_quota_reservations (
  generation_id UUID PRIMARY KEY REFERENCES generations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'reserved',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  usage_date DATE NOT NULL DEFAULT ((now() AT TIME ZONE 'utc')::date),
  CONSTRAINT generation_quota_reservation_status_check
    CHECK (status IN ('reserved', 'committed', 'released'))
);

CREATE INDEX idx_generation_quota_reservations_user
  ON generation_quota_reservations(user_id, status);

CREATE TABLE generation_daily_usage (
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  usage_date DATE NOT NULL,
  daily_limit INTEGER NOT NULL DEFAULT 3,
  reserved INTEGER NOT NULL DEFAULT 0,
  consumed INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, usage_date),
  CONSTRAINT generation_daily_usage_limit_positive CHECK (daily_limit >= 0),
  CONSTRAINT generation_daily_usage_reserved_non_negative CHECK (reserved >= 0),
  CONSTRAINT generation_daily_usage_consumed_non_negative CHECK (consumed >= 0),
  CONSTRAINT generation_daily_usage_not_over_limit CHECK (reserved + consumed <= daily_limit)
);

-- ---------------------------------------------------------------------
-- Admin monitoring views
-- ---------------------------------------------------------------------

CREATE VIEW admin_stats AS
SELECT
  (SELECT count(*) FROM profiles) AS total_accounts,
  (SELECT count(*) FROM brands) AS total_brands,
  (SELECT count(*) FROM generations) AS total_generations,
  (SELECT count(*) FROM generations WHERE status = 'pending') AS generations_pending,
  (SELECT count(*) FROM generations WHERE status = 'processing') AS generations_processing,
  (SELECT count(*) FROM generations WHERE status = 'succeeded') AS generations_succeeded,
  (SELECT count(*) FROM generations WHERE status = 'failed') AS generations_failed,
  (SELECT count(*) FROM generations WHERE provider = 'openai') AS generations_openai,
  (SELECT count(*) FROM generations WHERE provider = 'gemini') AS generations_gemini,
  (SELECT count(*) FROM generations WHERE created_at >= now() - interval '7 days') AS generations_last_7d,
  (SELECT count(*) FROM generations WHERE created_at >= now() - interval '30 days') AS generations_last_30d,
  (SELECT count(*) FROM brand_kits WHERE status = 'complete') AS brand_kits_complete,
  (SELECT count(*) FROM provider_keys WHERE is_active) AS active_provider_keys;

CREATE VIEW admin_brand_overview AS
SELECT
  b.id,
  b.name,
  b.owner_user_id,
  p.full_name AS owner_full_name,
  COALESCE(bk.status::text, 'not_started') AS kit_status,
  (SELECT count(*) FROM generations g WHERE g.brand_id = b.id) AS generation_count,
  EXISTS (
    SELECT 1
    FROM provider_keys pk
    WHERE pk.brand_id = b.id
      AND pk.is_active
  ) AS has_active_key,
  b.created_at
FROM brands b
LEFT JOIN profiles p ON p.user_id = b.owner_user_id
LEFT JOIN brand_kits bk ON bk.brand_id = b.id;

COMMENT ON VIEW admin_stats IS 'Single-row system-wide aggregate for the admin monitoring dashboard';
COMMENT ON VIEW admin_brand_overview IS 'Per-brand read-only overview for the admin monitoring dashboard';

-- ---------------------------------------------------------------------
-- Quota / credit / rate-limit functions (final versions)
-- ---------------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_available_credits(p_user_id uuid)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_balance integer;
    v_reserved integer;
BEGIN
    SELECT balance, reserved
    INTO v_balance, v_reserved
    FROM public.credit_accounts
    WHERE user_id = p_user_id;

    IF NOT FOUND THEN
        RETURN 0;
    END IF;

    RETURN greatest(coalesce(v_balance, 0) - coalesce(v_reserved, 0), 0);
END;
$$;

CREATE OR REPLACE FUNCTION reserve_generation_credit(
    p_user_id uuid,
    p_generation_id uuid,
    p_amount integer,
    p_idempotency_key text
)
RETURNS jsonb
LANGUAGE plpgsql
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

CREATE OR REPLACE FUNCTION commit_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION release_generation_credit(
    p_user_id uuid, p_generation_id uuid, p_reservation_id text, p_amount integer
) RETURNS jsonb LANGUAGE plpgsql AS $$
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

CREATE OR REPLACE FUNCTION _plan_limits_for_user(p_user_id uuid)
RETURNS TABLE(max_active_brands integer, lifetime_image_limit integer)
LANGUAGE sql
STABLE
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

CREATE OR REPLACE FUNCTION create_brand_if_allowed(
    p_user_id uuid,
    p_name text
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_limit integer;
    v_count integer;
    v_brand public.brands%ROWTYPE;
BEGIN
    SELECT max_active_brands INTO v_limit
    FROM public._plan_limits_for_user(p_user_id);

    -- Serialize brand creation per user so concurrent requests cannot exceed the limit.
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

CREATE OR REPLACE FUNCTION reserve_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
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

CREATE OR REPLACE FUNCTION commit_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
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

CREATE OR REPLACE FUNCTION release_generation_slot(
    p_user_id uuid,
    p_generation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
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

CREATE OR REPLACE FUNCTION get_generation_quota_summary(p_user_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
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

CREATE OR REPLACE FUNCTION check_generation_rate_limit(
    p_user_id uuid,
    p_bucket text,
    p_limit integer,
    p_window_started_at timestamptz
)
RETURNS jsonb
LANGUAGE plpgsql
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
