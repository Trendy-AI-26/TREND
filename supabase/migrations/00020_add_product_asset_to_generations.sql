# Add product_asset_id to generations table for connect generation table by 
# product_assets table

ALTER TABLE generations
ADD COLUMN product_asset_id UUID NULL
REFERENCES product_assets(id)
ON DELETE SET NULL; # If later delete the product asset, we don't want to delete 
# the generation, just set the reference to null

CREATE INDEX idx_generations_product_asset
  ON generations(product_asset_id);

COMMENT ON COLUMN generations.product_asset_id IS
  'Optional product reference image used for this generation';
