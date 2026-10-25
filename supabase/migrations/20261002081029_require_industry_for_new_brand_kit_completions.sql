ALTER TABLE public.brand_kits
  ADD CONSTRAINT chk_brand_kits_complete_requires_industry
  CHECK (
    status <> 'complete'
    OR (
      NULLIF(BTRIM(industry), '') IS NOT NULL
      AND NULLIF(BTRIM(audience), '') IS NOT NULL
      AND COALESCE(cardinality(colors), 0) >= 1
    )
  ) NOT VALID;

COMMENT ON CONSTRAINT chk_brand_kits_complete_requires_industry ON public.brand_kits IS
  'New or updated completed kits require a non-empty industry, audience, and at least one color; legacy rows are preserved.';;
