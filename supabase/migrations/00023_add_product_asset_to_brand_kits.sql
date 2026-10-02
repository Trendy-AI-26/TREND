ALTER TABLE brand_kits
  ADD COLUMN product_asset_id UUID REFERENCES product_assets(id) ON DELETE SET NULL;

ALTER TABLE product_assets
  DROP CONSTRAINT chk_product_assets_file_size,
  ADD CONSTRAINT chk_product_assets_file_size
    CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760);

UPDATE storage.buckets
SET file_size_limit = 10485760
WHERE id = 'product-assets';

COMMENT ON COLUMN brand_kits.product_asset_id IS
  'Product image selected during brand identity setup';