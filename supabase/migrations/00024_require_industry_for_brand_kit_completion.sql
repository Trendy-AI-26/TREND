ALTER TABLE brand_kits
  DROP CONSTRAINT chk_brand_kits_status_complete_consistency;

UPDATE brand_kits
SET
  tone = NULL,
  status = CASE
    WHEN status = 'complete' AND industry IS NULL THEN 'in_progress'::kit_status_t
    ELSE status
  END,
  completed_at = CASE
    WHEN status = 'complete' AND industry IS NULL THEN NULL
    ELSE completed_at
  END;

ALTER TABLE brand_kits
  ADD CONSTRAINT chk_brand_kits_status_complete_consistency
  CHECK (
    (status = 'complete' AND industry IS NOT NULL AND audience IS NOT NULL AND cardinality(colors) >= 1)
    OR
    (status != 'complete')
  );