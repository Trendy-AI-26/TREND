-- Require industry for new completed-kit writes without rewriting legacy data.
--
-- NOT VALID deliberately leaves existing rows untouched. PostgreSQL still
-- enforces this CHECK for every new row and every future INSERT/UPDATE. A
-- legacy completed kit can therefore remain visible as-is until its owner
-- edits it, while all newly saved completed kits require industry, audience,
-- and at least one color.

ALTER TABLE brand_kits
  ADD CONSTRAINT chk_brand_kits_complete_requires_industry
  CHECK (
    status <> 'complete'
    OR (
      NULLIF(BTRIM(industry), '') IS NOT NULL
      AND NULLIF(BTRIM(audience), '') IS NOT NULL
      AND COALESCE(cardinality(colors), 0) >= 1
    )
  ) NOT VALID;

COMMENT ON CONSTRAINT chk_brand_kits_complete_requires_industry ON brand_kits IS
  'New or updated completed kits require a non-empty industry, audience, and at least one color; legacy rows are preserved.';
