ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS avatar_path TEXT;

COMMENT ON COLUMN profiles.avatar_path IS
'Private storage path for the user avatar';
