-- PROPOSAL ONLY: do not run manually or apply to production.
-- Promote through a reviewed Supabase migration after the GitHub PR is approved.
-- All writes happen through narrow authenticated RPCs. Clients cannot edit ledgers.

create table if not exists public.sowia_agent_usage_monthly (
    user_id uuid not null references auth.users(id) on delete cascade,
    month_start date not null,
    credits_used integer not null default 0 check (credits_used >= 0),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (user_id, month_start)
);

create table if not exists public.sowia_agent_usage_events (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    request_id uuid not null,
    month_start date not null,
    action text not null check (action in ('chat', 'web_search', 'code_generation', 'file_analysis', 'tool_execution')),
    credits integer not null check (credits > 0),
    used_after integer not null check (used_after >= credits),
    created_at timestamptz not null default now(),
    unique (user_id, request_id)
);

create index if not exists sowia_agent_usage_events_user_month_idx
    on public.sowia_agent_usage_events (user_id, month_start, created_at desc);

alter table public.sowia_agent_usage_monthly enable row level security;
alter table public.sowia_agent_usage_events enable row level security;

-- Direct table access is denied. The RPCs below are the only access path.
revoke all on table public.sowia_agent_usage_monthly from public, anon, authenticated;
revoke all on table public.sowia_agent_usage_events from public, anon, authenticated;
revoke all on sequence public.sowia_agent_usage_events_id_seq from public, anon, authenticated;

create or replace function public.sowia_get_agent_usage()
returns table (
    month_start date,
    used_credits integer,
    monthly_limit integer,
    remaining_credits integer
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_month_start date := (date_trunc('month', now() at time zone 'UTC'))::date;
    v_used integer := 0;
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;

    select coalesce(u.credits_used, 0)
      into v_used
      from public.sowia_agent_usage_monthly as u
     where u.user_id = v_user_id
       and u.month_start = v_month_start;

    return query select v_month_start, v_used, 1000, greatest(0, 1000 - v_used);
end;
$$;

create or replace function public.sowia_consume_agent_credits(
    p_request_id uuid,
    p_action text
)
returns table (
    allowed boolean,
    used_credits integer,
    monthly_limit integer,
    remaining_credits integer,
    reason text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
    v_month_start date := (date_trunc('month', now() at time zone 'UTC'))::date;
    v_cost integer;
    v_used integer;
    v_existing public.sowia_agent_usage_events%rowtype;
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;
    if p_request_id is null then
        raise exception 'Request id required' using errcode = '22023';
    end if;

    v_cost := case p_action
        when 'chat' then 1
        when 'web_search' then 3
        when 'code_generation' then 5
        when 'file_analysis' then 4
        when 'tool_execution' then 2
        else null
    end;
    if v_cost is null then
        raise exception 'Unsupported agent action' using errcode = '22023';
    end if;

    -- Serialize retries of the same request so they cannot debit twice.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(v_user_id::text || ':' || p_request_id::text, 0)
    );

    select e.* into v_existing
      from public.sowia_agent_usage_events as e
     where e.user_id = v_user_id
       and e.request_id = p_request_id;

    if found then
        return query select true, v_existing.used_after, 1000,
            greatest(0, 1000 - v_existing.used_after), 'already_recorded'::text;
        return;
    end if;

    insert into public.sowia_agent_usage_monthly (user_id, month_start, credits_used)
    values (v_user_id, v_month_start, 0)
    on conflict (user_id, month_start) do nothing;

    update public.sowia_agent_usage_monthly as u
       set credits_used = u.credits_used + v_cost,
           updated_at = now()
     where u.user_id = v_user_id
       and u.month_start = v_month_start
       and u.credits_used + v_cost <= 1000
     returning u.credits_used into v_used;

    if not found then
        select u.credits_used into v_used
          from public.sowia_agent_usage_monthly as u
         where u.user_id = v_user_id
           and u.month_start = v_month_start;
        return query select false, coalesce(v_used, 0), 1000,
            greatest(0, 1000 - coalesce(v_used, 0)), 'quota_exceeded'::text;
        return;
    end if;

    insert into public.sowia_agent_usage_events (
        user_id, request_id, month_start, action, credits, used_after
    ) values (
        v_user_id, p_request_id, v_month_start, p_action, v_cost, v_used
    );

    return query select true, v_used, 1000, greatest(0, 1000 - v_used), 'quota_available'::text;
end;
$$;

-- SECURITY DEFINER is restricted to authenticated callers only. The functions
-- derive the account from auth.uid(); callers cannot submit a different owner.
revoke all on function public.sowia_get_agent_usage() from public, anon;
revoke all on function public.sowia_consume_agent_credits(uuid, text) from public, anon;
grant execute on function public.sowia_get_agent_usage() to authenticated;
grant execute on function public.sowia_consume_agent_credits(uuid, text) to authenticated;
