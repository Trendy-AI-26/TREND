-- Reconcile schema changes that were applied safely while the remote project
-- was ahead of its local migration history. This migration is idempotent and
-- does not rewrite Brand Kit answers or statuses.

ALTER TABLE public.generations
  ADD COLUMN IF NOT EXISTS brief JSONB;

COMMENT ON COLUMN public.generations.brief IS
  'Snapshot of the structured generation questionnaire used for downstream caption generation';

CREATE INDEX IF NOT EXISTS idx_product_assets_brand_created
  ON public.product_assets(brand_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_product_assets_owner
  ON public.product_assets(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_generations_product_asset
  ON public.generations(product_asset_id);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.brand_kits'::regclass AND conname='chk_brand_kits_industry_length') THEN
    ALTER TABLE public.brand_kits ADD CONSTRAINT chk_brand_kits_industry_length CHECK (industry IS NULL OR LENGTH(TRIM(industry)) <= 120);
  END IF;
END
$$;

ALTER TABLE public.brand_kits
  ADD COLUMN IF NOT EXISTS product_asset_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.brand_kits'::regclass AND conname='brand_kits_product_asset_id_fkey') THEN
    ALTER TABLE public.brand_kits ADD CONSTRAINT brand_kits_product_asset_id_fkey FOREIGN KEY (product_asset_id) REFERENCES public.product_assets(id) ON DELETE SET NULL;
  END IF;
END
$$;

ALTER TABLE public.product_assets DROP CONSTRAINT IF EXISTS chk_product_assets_file_size;
ALTER TABLE public.product_assets ADD CONSTRAINT chk_product_assets_file_size CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760);

UPDATE storage.buckets SET file_size_limit = 10485760 WHERE id = 'product-assets';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='Product assets owner can read') THEN
    CREATE POLICY "Product assets owner can read" ON storage.objects FOR SELECT TO authenticated
    USING (bucket_id='product-assets' AND EXISTS (SELECT 1 FROM public.brands WHERE brands.id=(storage.foldername(name))[2]::UUID AND brands.owner_user_id=auth.uid()));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='Product assets owner can upload') THEN
    CREATE POLICY "Product assets owner can upload" ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (bucket_id='product-assets' AND EXISTS (SELECT 1 FROM public.brands WHERE brands.id=(storage.foldername(name))[2]::UUID AND brands.owner_user_id=auth.uid()));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='Product assets owner can update') THEN
    CREATE POLICY "Product assets owner can update" ON storage.objects FOR UPDATE TO authenticated
    USING (bucket_id='product-assets' AND EXISTS (SELECT 1 FROM public.brands WHERE brands.id=(storage.foldername(name))[2]::UUID AND brands.owner_user_id=auth.uid()) )
    WITH CHECK (bucket_id='product-assets' AND EXISTS (SELECT 1 FROM public.brands WHERE brands.id=(storage.foldername(name))[2]::UUID AND brands.owner_user_id=auth.uid()) );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='storage' AND tablename='objects' AND policyname='Product assets owner can delete') THEN
    CREATE POLICY "Product assets owner can delete" ON storage.objects FOR DELETE TO authenticated
    USING (bucket_id='product-assets' AND EXISTS (SELECT 1 FROM public.brands WHERE brands.id=(storage.foldername(name))[2]::UUID AND brands.owner_user_id=auth.uid()));
  END IF;
END
$$;
***
