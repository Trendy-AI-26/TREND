# Create private product-assets bucket for storing product reference images

INSERT INTO storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
VALUES (
  'product-assets',
  'product-assets',
  false,
  5242880,
  ARRAY[
    'image/png',
    'image/jpeg',
    'image/webp'
  ]
)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Product assets owner can read"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'product-assets'
  AND EXISTS (
    SELECT 1
    FROM brands
    WHERE brands.id = (storage.foldername(name))[2]::UUID
      AND brands.owner_user_id = auth.uid()
  )
);

CREATE POLICY "Product assets owner can upload"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'product-assets'
  AND EXISTS (
    SELECT 1
    FROM brands
    WHERE brands.id = (storage.foldername(name))[2]::UUID
      AND brands.owner_user_id = auth.uid()
  )
);

# Add storage.objects table policies to allow users to update and delete their 
# own product assets

CREATE POLICY "Product assets owner can update"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'product-assets'
  AND EXISTS (
    SELECT 1
    FROM brands
    WHERE brands.id = (storage.foldername(name))[2]::UUID
      AND brands.owner_user_id = auth.uid()
  )
)
WITH CHECK (
  bucket_id = 'product-assets'
  AND EXISTS (
    SELECT 1
    FROM brands
    WHERE brands.id = (storage.foldername(name))[2]::UUID
      AND brands.owner_user_id = auth.uid()
  )
);

CREATE POLICY "Product assets owner can delete"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'product-assets'
  AND EXISTS (
    SELECT 1
    FROM brands
    WHERE brands.id = (storage.foldername(name))[2]::UUID
      AND brands.owner_user_id = auth.uid()
  )
);
