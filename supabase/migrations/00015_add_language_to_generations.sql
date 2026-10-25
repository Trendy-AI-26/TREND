-- Store the selected text language for each generation.
ALTER TABLE public.generations
ADD COLUMN language text NOT NULL DEFAULT 'ar';

ALTER TABLE public.generations
ADD CONSTRAINT chk_generations_language
CHECK (language IN ('ar', 'en'));

COMMENT ON COLUMN public.generations.language IS
'Text language selected for the generation: ar or en';
