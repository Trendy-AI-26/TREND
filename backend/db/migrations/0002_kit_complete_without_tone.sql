-- The brand kit wizard no longer asks for a tone, and the app marks a kit
-- "complete" once industry, audience and at least one colour are set
-- (app/services/kit_summary.py:derive_status). The original constraint still
-- required tone IS NOT NULL, so saving a complete kit failed with HTTP 500.
-- Industry/audience/colours remain enforced by
-- chk_brand_kits_complete_requires_industry.

ALTER TABLE brand_kits
  DROP CONSTRAINT IF EXISTS chk_brand_kits_status_complete_consistency;

ALTER TABLE brand_kits
  ADD CONSTRAINT chk_brand_kits_status_complete_consistency
  CHECK (
    status <> 'complete'
    OR (audience IS NOT NULL AND cardinality(colors) >= 1)
  );
