-- Add a private storage path for user avatars.
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS avatar_path TEXT;

ALTER TABLE public.profiles
DROP CONSTRAINT IF EXISTS chk_profiles_avatar_path_format;

ALTER TABLE public.profiles
ADD CONSTRAINT chk_profiles_avatar_path_format
CHECK (
  avatar_path IS NULL
  OR avatar_path ~ '^avatars/[0-9a-f-]+/avatar\.(png|jpg|webp)$'
);

COMMENT ON COLUMN public.profiles.avatar_path IS
'Private Storage path for the user avatar';
