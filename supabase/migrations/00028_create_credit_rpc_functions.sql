create or replace function public.get_available_credits(
    p_user_id uuid
)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance integer;
    v_reserved integer;
begin
    select
        balance,
        reserved
    into
        v_balance,
        v_reserved
    from public.credit_accounts
    where user_id = p_user_id;

    if not found then
        return 0;
    end if;

    return greatest(
        coalesce(v_balance, 0)
        - coalesce(v_reserved, 0),
        0
    );

create or replace function public.reserve_generation_credit(
    p_user_id uuid,
    p_generation_id uuid,
    p_amount integer,
    p_idempotency_key text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance integer;
    v_reserved integer;
    v_available integer;
    v_existing_id uuid;
begin
    if p_amount <= 0 then
        raise exception 'INVALID_CREDIT_AMOUNT';
    end if;

    select id
    into v_existing_id
    from public.credit_ledger
    where user_id = p_user_id
      and idempotency_key = p_idempotency_key
    limit 1;

    if v_existing_id is not null then
        raise exception 'IDEMPOTENCY_KEY_REUSED';
    end if;

    insert into public.credit_accounts (
        user_id,
        balance,
        reserved
    )
    values (
        p_user_id,
        0,
        0
    )
    on conflict (user_id) do nothing;

    select
        balance,
        reserved
    into
        v_balance,
        v_reserved
    from public.credit_accounts
    where user_id = p_user_id
    for update;

    v_available := greatest(
        coalesce(v_balance, 0)
        - coalesce(v_reserved, 0),
        0
    );

    if v_available < p_amount then
        raise exception 'INSUFFICIENT_CREDITS';
    end if;

    update public.credit_accounts
    set reserved = reserved + p_amount,
        updated_at = now()
    where user_id = p_user_id;

    insert into public.credit_ledger (
        user_id,
        generation_id,
        operation,
        amount,
        idempotency_key,
        metadata
    )
    values (
        p_user_id,
        p_generation_id,
        'reserve',
        p_amount,
        p_idempotency_key,
        jsonb_build_object(
            'amount', p_amount,
            'generation_id', p_generation_id
        )
    );

    return jsonb_build_object(
        'reservation_id', p_idempotency_key,
        'user_id', p_user_id,
        'generation_id', p_generation_id,
        'amount', p_amount
    );

create or replace function public.commit_generation_credit(
    p_user_id uuid,
    p_generation_id uuid,
    p_reservation_id text,
    p_amount integer
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    v_balance integer;
    v_reserved integer;
begin
    select
        balance,
        reserved
    into
        v_balance,
        v_reserved
    from public.credit_accounts
    where user_id = p_user_id
    for update;

    if not found then
        raise exception 'CREDIT_ACCOUNT_NOT_FOUND';
    end if;

    update public.credit_accounts
    set balance = greatest(balance - p_amount, 0),
        reserved = greatest(reserved - p_amount, 0),
        updated_at = now()
    where user_id = p_user_id;

    insert into public.credit_ledger (
        user_id,
        generation_id,
        operation,
        amount,
        idempotency_key,
        metadata
    )
    values (
        p_user_id,
        p_generation_id,
        'commit',
        -p_amount,
        p_reservation_id || '-commit',
        '{}'::jsonb
    )
    on conflict (idempotency_key) do nothing;

    return jsonb_build_object(
        'status', 'committed',
        'amount', p_amount
    );

create or replace function public.release_generation_credit(
    p_user_id uuid,
    p_generation_id uuid,
    p_reservation_id text,
    p_amount integer
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.credit_accounts
    set reserved = greatest(reserved - p_amount, 0),
        updated_at = now()
    where user_id = p_user_id;

    if not found then
        raise exception 'CREDIT_ACCOUNT_NOT_FOUND';
    end if;

    insert into public.credit_ledger (
        user_id,
        generation_id,
        operation,
        amount,
        idempotency_key,
        metadata
    )
    values (
        p_user_id,
        p_generation_id,
        'release',
        p_amount,
        p_reservation_id || '-release',
        '{}'::jsonb
    )
    on conflict (idempotency_key) do nothing;

    return jsonb_build_object(
        'status', 'released',
        'amount', p_amount
    );


