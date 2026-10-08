create table if not exists public.generation_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  generation_id uuid references public.generations(id) on delete set null,
  operation text not null,
  provider text not null,
  model text not null,
  status text not null,
  credits_charged integer not null default 0,
  estimated_provider_cost numeric(12, 6),
  provider_request_id text,
  error_code text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);
