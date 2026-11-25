-- PROPOSAL ONLY: apply only after review and approval of the agent feature stack.
-- Adds per-agent tool permissions and owner-visible, quota-linked activity history.
-- No payment, checkout, or automatic overage behavior is introduced.

alter table public.sowia_agents
    add column if not exists enabled_tools text[] not null
    default array['memory_read', 'memory_write']::text[];

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'sowia_agents_enabled_tools_allowed'
          and conrelid = 'public.sowia_agents'::regclass
    ) then
        alter table public.sowia_agents
            add constraint sowia_agents_enabled_tools_allowed
            check (
                enabled_tools <@ array['web_search', 'memory_read', 'memory_write']::text[]
                and cardinality(enabled_tools) <= 3
            );
    end if;
end;
$$;

create unique index if not exists sowia_agents_id_owner_workspace_uidx
    on public.sowia_agents (id, user_id, workspace_id);

create table if not exists public.sowia_agent_activity_events (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    agent_id uuid not null references public.sowia_agents(id) on delete cascade,
    workspace_id text not null check (workspace_id in ('personal', 'professional')),
    request_id uuid not null,
    tool_name text not null check (tool_name in ('agent_chat', 'web_search', 'memory_read', 'memory_write')),
    action text not null check (action in ('chat', 'web_search', 'tool_execution')),
    credits integer not null check (credits > 0),
    used_after integer not null check (used_after >= credits),
    status text not null default 'started'
        check (status in ('started', 'completed', 'failed')),
    error_code text,
    created_at timestamptz not null default now(),
    finished_at timestamptz,
    unique (user_id, request_id),
    constraint sowia_agent_activity_scope_fk
        foreign key (agent_id, user_id, workspace_id)
        references public.sowia_agents(id, user_id, workspace_id)
        on delete cascade
);

create index if not exists sowia_agent_activity_owner_agent_idx
    on public.sowia_agent_activity_events
    (user_id, agent_id, created_at desc);

alter table public.sowia_agent_activity_events enable row level security;
revoke all on table public.sowia_agent_activity_events from public, anon, authenticated;
revoke all on sequence public.sowia_agent_activity_events_id_seq from public, anon, authenticated;

-- One atomic operation: debit quota and create the agent-attributed history row.
create or replace function public.sowia_consume_agent_action_for_agent(
    p_request_id uuid,
    p_action text,
    p_agent_id uuid,
    p_workspace_id text,
    p_tool_name text
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
    v_agent public.sowia_agents%rowtype;
    v_usage record;
    v_event public.sowia_agent_activity_events%rowtype;
    v_expected_action text;
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;
    if p_request_id is null or p_agent_id is null then
        raise exception 'Request and agent identifiers are required' using errcode = '22023';
    end if;
    if p_workspace_id not in ('personal', 'professional') then
        raise exception 'Invalid workspace' using errcode = '22023';
    end if;
    if p_tool_name not in ('agent_chat', 'web_search', 'memory_read', 'memory_write') then
        raise exception 'Unsupported agent tool' using errcode = '22023';
    end if;

    select a.* into v_agent
      from public.sowia_agents a
     where a.id = p_agent_id
       and a.user_id = v_user_id
       and a.workspace_id = p_workspace_id
       and a.status = 'active';
    if not found or (p_tool_name <> 'agent_chat' and not (p_tool_name = any(v_agent.enabled_tools))) then
        raise exception 'Agent tool is not enabled for this owner' using errcode = '42501';
    end if;

    v_expected_action := case
        when p_tool_name = 'agent_chat' then 'chat'
        when p_tool_name = 'web_search' then 'web_search'
        else 'tool_execution'
    end;
    if p_action <> v_expected_action then
        raise exception 'Tool and quota action do not match' using errcode = '22023';
    end if;

    select e.* into v_event
      from public.sowia_agent_activity_events e
     where e.user_id = v_user_id and e.request_id = p_request_id;
    if found then
        if v_event.agent_id <> p_agent_id
           or v_event.tool_name <> p_tool_name
           or v_event.action <> p_action then
            raise exception 'Request id is already assigned to another agent action'
                using errcode = '42501';
        end if;
        return query select true, v_event.used_after, 1000,
            greatest(0, 1000 - v_event.used_after), 'already_recorded'::text;
        return;
    end if;

    select * into v_usage
      from public.sowia_consume_agent_credits(p_request_id, p_action);

    if v_usage.reason = 'already_recorded'
       and not exists (
           select 1 from public.sowia_agent_activity_events e
            where e.user_id = v_user_id and e.request_id = p_request_id
       ) then
        raise exception 'Request id was already consumed outside this agent activity.'
            using errcode = '42501';
    end if;

    if v_usage.allowed then
        insert into public.sowia_agent_activity_events (
            user_id, agent_id, workspace_id, request_id, tool_name,
            action, credits, used_after, status
        ) values (
            v_user_id, p_agent_id, p_workspace_id, p_request_id, p_tool_name,
            p_action,
            case p_action when 'chat' then 1 when 'web_search' then 3 else 2 end,
            v_usage.used_credits, 'started'
        )
        on conflict (user_id, request_id) do nothing;

        select e.* into v_event
          from public.sowia_agent_activity_events e
         where e.user_id = v_user_id and e.request_id = p_request_id;
        if not found or v_event.agent_id <> p_agent_id
           or v_event.tool_name <> p_tool_name or v_event.action <> p_action then
            raise exception 'Agent activity could not be safely recorded'
                using errcode = '42501';
        end if;
    end if;

    return query select v_usage.allowed, v_usage.used_credits,
        v_usage.monthly_limit, v_usage.remaining_credits, v_usage.reason;
end;
$$;

create or replace function public.sowia_finish_agent_action_for_agent(
    p_request_id uuid,
    p_agent_id uuid,
    p_status text,
    p_error_code text default null
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;
    if p_status not in ('completed', 'failed') then
        raise exception 'Invalid activity status' using errcode = '22023';
    end if;

    update public.sowia_agent_activity_events
       set status = p_status,
           error_code = case when p_status = 'failed'
               then left(coalesce(p_error_code, 'AgentActionFailed'), 80)
               else null end,
           finished_at = now()
     where user_id = v_user_id
       and agent_id = p_agent_id
       and request_id = p_request_id
       and status = 'started';

    return found;
end;
$$;

create or replace function public.sowia_get_agent_activity(
    p_agent_id uuid,
    p_limit integer default 20
)
returns table (
    total_credits bigint,
    total_actions bigint,
    request_id uuid,
    tool_name text,
    action text,
    credits integer,
    status text,
    error_code text,
    created_at timestamptz,
    finished_at timestamptz,
    used_after integer
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := auth.uid();
begin
    if v_user_id is null then
        raise exception 'Authentication required' using errcode = '42501';
    end if;
    if p_limit is null or p_limit < 1 or p_limit > 50 then
        raise exception 'Limit must be between 1 and 50' using errcode = '22023';
    end if;
    if not exists (
        select 1 from public.sowia_agents a
         where a.id = p_agent_id and a.user_id = v_user_id
    ) then
        raise exception 'Agent not found' using errcode = '42501';
    end if;

    return query
    with totals as (
        select coalesce(sum(e.credits), 0)::bigint as credits,
               count(*)::bigint as actions
          from public.sowia_agent_activity_events e
         where e.user_id = v_user_id and e.agent_id = p_agent_id
    ),
    recent as (
        select e.request_id, e.tool_name, e.action, e.credits, e.status,
               e.error_code, e.created_at, e.finished_at, e.used_after
          from public.sowia_agent_activity_events e
         where e.user_id = v_user_id and e.agent_id = p_agent_id
         order by e.created_at desc
         limit p_limit
    )
    select totals.credits, totals.actions, recent.request_id, recent.tool_name,
           recent.action, recent.credits, recent.status, recent.error_code,
           recent.created_at, recent.finished_at, recent.used_after
      from totals left join recent on true
     order by recent.created_at desc nulls last;
end;
$$;

revoke all on function public.sowia_consume_agent_action_for_agent(uuid, text, uuid, text, text)
    from public, anon;
revoke all on function public.sowia_finish_agent_action_for_agent(uuid, uuid, text, text)
    from public, anon;
revoke all on function public.sowia_get_agent_activity(uuid, integer)
    from public, anon;

grant execute on function public.sowia_consume_agent_action_for_agent(uuid, text, uuid, text, text)
    to authenticated;
grant execute on function public.sowia_finish_agent_action_for_agent(uuid, uuid, text, text)
    to authenticated;
grant execute on function public.sowia_get_agent_activity(uuid, integer)
    to authenticated;

comment on table public.sowia_agent_activity_events is
    'Per-agent, owner-scoped record of quota-gated tool invocations; contains no prompt or result content.';
