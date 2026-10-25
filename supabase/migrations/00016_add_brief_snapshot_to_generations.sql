-- Preserve the questionnaire context used to create an image.
-- Caption generation inherits this snapshot and never asks the user to repeat it.

ALTER TABLE generations
  ADD COLUMN brief JSONB;

COMMENT ON COLUMN generations.brief IS
  'Snapshot of the structured generation questionnaire used for downstream caption generation';
