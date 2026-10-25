ALTER TABLE brand_kits
  ADD COLUMN industry TEXT,
  ADD CONSTRAINT chk_brand_kits_industry_length
    CHECK (industry IS NULL OR LENGTH(TRIM(industry)) <= 120);

COMMENT ON COLUMN brand_kits.industry IS 'Brand industry or business category';