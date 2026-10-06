create table if not exists public.plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  image_credits integer not null check (image_credits >= 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
insert into public.plans (
  code,
  name,
  image_credits
)
values (
  'beta',
  'Beta',
  3
)
on conflict (code) do nothing;

create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_id uuid not null references public.plans(id),
  status text not null default 'active',
  period_start timestamptz not null default now(),
  period_end timestamptz not null,
  stripe_customer_id text,
  stripe_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index if not exists
subscriptions_one_active_per_user
on public.subscriptions(user_id)
where status = 'active';
