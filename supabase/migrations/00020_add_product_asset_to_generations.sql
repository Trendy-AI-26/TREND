-- Add an optional product reference image to a generation.

ALTER TABLE generations
ADD COLUMN product_asset_id UUID NULL
REFERENCES product_assets(id)
ON DELETE SET NULL;

-- Deleting a product asset keeps the generation and clears this reference.

CREATE INDEX idx_generations_product_asset
  ON generations(product_asset_id);

COMMENT ON COLUMN generations.product_asset_id IS
  'Optional product reference image used for this generation';
