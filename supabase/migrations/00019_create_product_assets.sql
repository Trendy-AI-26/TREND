-- Product Assets Table Created by Supabase CLI

-- Product reference images uploaded by users for generation requests

CREATE TABLE product_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  brand_id UUID NOT NULL
    REFERENCES brands(id)
    ON DELETE CASCADE,

  owner_user_id UUID NOT NULL
    REFERENCES auth.users(id)
    ON DELETE CASCADE,

  storage_path TEXT NOT NULL UNIQUE,

  content_type TEXT NOT NULL,

  file_size_bytes BIGINT NOT NULL,

  width INT NOT NULL,

  height INT NOT NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  deleted_at TIMESTAMPTZ
);

ALTER TABLE product_assets
  ADD CONSTRAINT chk_product_assets_storage_path
  CHECK (
    storage_path ~ '^brands/[0-9a-f-]+/product-assets/[0-9a-f-]+\.(png|jpg|webp)$'
  );

ALTER TABLE product_assets
  ADD CONSTRAINT chk_product_assets_content_type
  CHECK (
    content_type IN ('image/png', 'image/jpeg', 'image/webp')
  );

ALTER TABLE product_assets
  ADD CONSTRAINT chk_product_assets_file_size
  CHECK (
    file_size_bytes > 0
    AND file_size_bytes <= 5242880
  );

ALTER TABLE product_assets
  ADD CONSTRAINT chk_product_assets_dimensions
  CHECK (
    width > 0
    AND width <= 8192
    AND height > 0
    AND height <= 8192
  );

CREATE INDEX idx_product_assets_brand_created
  ON product_assets(brand_id, created_at DESC);

CREATE INDEX idx_product_assets_owner
  ON product_assets(owner_user_id);

COMMENT ON TABLE product_assets IS
  'Optional product reference images used during generation';

COMMENT ON COLUMN product_assets.storage_path IS
  'Private Storage path for the product image';

-- This owner column makes it easy to query assets by uploader and enforces that
-- the uploader exists in auth.users.

COMMENT ON COLUMN product_assets.owner_user_id IS  

  'User who uploaded the product image';
