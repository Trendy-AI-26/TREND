-- Require industry for completed brand kits without discarding existing answers.
--
-- Existing completed kits that do not satisfy the new completion contract are
-- moved back to in_progress so they can be completed from the UI. Their
-- answers, including tone, tagline, audience, colors, and avoid_words, are
-- intentionally preserved.

ALTER TABLE brand_kits
  DROP CONSTRAINT chk_brand_kits_status_complete_consistency;

UPDATE brand_kits
SET
  status = 'in_progress'::kit_status_t,
  completed_at = NULL
WHERE status = 'complete'
  AND (
    NULLIF(BTRIM(industry), '') IS NULL
    OR NULLIF(BTRIM(audience), '') IS NULL
    OR COALESCE(cardinality(colors), 0) < 1
  );

ALTER TABLE brand_kits
  ADD CONSTRAINT chk_brand_kits_status_complete_consistency
  CHECK (
    (
      status = 'complete'
      AND NULLIF(BTRIM(industry), '') IS NOT NULL
      AND NULLIF(BTRIM(audience), '') IS NOT NULL
      AND COALESCE(cardinality(colors), 0) >= 1
    )
    OR status <> 'complete'
  );

COMMENT ON CONSTRAINT chk_brand_kits_status_complete_consistency ON brand_kits IS
  'Completed kits require a non-empty industry, audience, and at least one color; existing answers are preserved.';
