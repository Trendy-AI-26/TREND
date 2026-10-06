create table if not exists public.generation_captions (
  id uuid primary key default gen_random_uuid(),
  generation_id uuid not null references public.generations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  language text not null,
  platform text not null,
  caption_text text not null,
  hashtags jsonb not null default '[]'::jsonb,
  keywords jsonb not null default '[]'::jsonb,
  provider text not null,
  model text not null,
  prompt_version text,
  created_at timestamptz not null default now()
);
