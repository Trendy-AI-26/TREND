ALTER TABLE brand_kits
  DROP CONSTRAINT chk_brand_kits_colors_count;

ALTER TABLE brand_kits
  ADD CONSTRAINT chk_brand_kits_colors_count
  CHECK (cardinality(colors) <= 4);

COMMENT ON COLUMN brand_kits.colors IS 'Brand colors (array of hex codes, max 4)';
