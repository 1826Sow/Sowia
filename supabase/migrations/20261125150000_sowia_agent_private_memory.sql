-- Persistent, owner-controlled AI agent registry and private agent memories.
-- Additive only: existing user memories and project links remain untouched.

create table if not exists public.sowia_agents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'personal'
        check (workspace_id in ('personal', 'professional')),
    project_id bigint,
    name text not null check (char_length(name) between 1 and 120),
    description text not null default '' check (char_length(description) <= 2000),
    can_read_workspace_memory boolean not null default false,
    can_read_project_memory boolean not null default false,
    can_write_private_memory boolean not null default true,
    status text not null default 'active' check (status in ('active', 'paused', 'archived')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sowia_agents_project_fk
        foreign key (project_id) references public.sowia_projects(id) on delete set null
);

create index if not exists sowia_agents_owner_workspace_idx
    on public.sowia_agents (user_id, workspace_id, status, updated_at desc);
create index if not exists sowia_agents_project_idx
    on public.sowia_agents (project_id) where project_id is not null;

alter table public.sowia_agents enable row level security;

drop policy if exists sowia_agents_select_own on public.sowia_agents;
create policy sowia_agents_select_own on public.sowia_agents
    for select to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists sowia_agents_insert_own on public.sowia_agents;
create policy sowia_agents_insert_own on public.sowia_agents
    for insert to authenticated
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists sowia_agents_update_own on public.sowia_agents;
create policy sowia_agents_update_own on public.sowia_agents
    for update to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    )
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists sowia_agents_delete_own on public.sowia_agents;
create policy sowia_agents_delete_own on public.sowia_agents
    for delete to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

grant select, insert, update, delete on public.sowia_agents to authenticated;

create table if not exists public.sowia_agent_memory_items (
    id bigint generated always as identity primary key,
    agent_id uuid not null references public.sowia_agents(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null check (workspace_id in ('personal', 'professional')),
    content text not null check (char_length(content) between 1 and 4000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sowia_agent_memory_owner_idx
    on public.sowia_agent_memory_items (user_id, workspace_id, agent_id, created_at desc);

alter table public.sowia_agent_memory_items enable row level security;

drop policy if exists sowia_agent_memory_select_own on public.sowia_agent_memory_items;
create policy sowia_agent_memory_select_own on public.sowia_agent_memory_items
    for select to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_memory_items.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_memory_items.workspace_id
              and a.status = 'active'
        )
    );

drop policy if exists sowia_agent_memory_insert_own on public.sowia_agent_memory_items;
create policy sowia_agent_memory_insert_own on public.sowia_agent_memory_items
    for insert to authenticated
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_memory_items.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_memory_items.workspace_id
              and a.status = 'active'
              and a.can_write_private_memory
        )
    );

drop policy if exists sowia_agent_memory_update_own on public.sowia_agent_memory_items;
create policy sowia_agent_memory_update_own on public.sowia_agent_memory_items
    for update to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_memory_items.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_memory_items.workspace_id
              and a.status = 'active'
              and a.can_write_private_memory
        )
    )
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_memory_items.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_memory_items.workspace_id
              and a.status = 'active'
              and a.can_write_private_memory
        )
    );

drop policy if exists sowia_agent_memory_delete_own on public.sowia_agent_memory_items;
create policy sowia_agent_memory_delete_own on public.sowia_agent_memory_items
    for delete to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

grant select, insert, update, delete on public.sowia_agent_memory_items to authenticated;
grant usage, select on sequence public.sowia_agent_memory_items_id_seq to authenticated;

-- An agent's optional project must remain in the same owner/workspace and active.
create or replace function public.sowia_validate_agent_project_scope()
returns trigger
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
begin
    if new.project_id is not null and not exists (
        select 1 from public.sowia_projects p
        where p.id = new.project_id
          and p.user_id = new.user_id
          and p.workspace_id = new.workspace_id
          and p.archived_at is null
    ) then
        raise exception 'Agent project must belong to the same active owner and workspace.'
            using errcode = '42501';
    end if;
    return new;
end;
$function$;

drop trigger if exists sowia_agent_project_scope_guard on public.sowia_agents;
create trigger sowia_agent_project_scope_guard
    before insert or update of project_id, user_id, workspace_id
    on public.sowia_agents
    for each row execute function public.sowia_validate_agent_project_scope();

-- Prevent forged user/workspace/agent combinations on private agent memories.
create or replace function public.sowia_validate_agent_memory_scope()
returns trigger
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
begin
    if not exists (
        select 1 from public.sowia_agents a
        where a.id = new.agent_id
          and a.user_id = new.user_id
          and a.workspace_id = new.workspace_id
          and a.status = 'active'
          and a.can_write_private_memory
    ) then
        raise exception 'Agent memory must belong to an active authorized agent.'
            using errcode = '42501';
    end if;
    return new;
end;
$function$;

drop trigger if exists sowia_agent_memory_scope_guard on public.sowia_agent_memory_items;
create trigger sowia_agent_memory_scope_guard
    before insert or update of agent_id, user_id, workspace_id
    on public.sowia_agent_memory_items
    for each row execute function public.sowia_validate_agent_memory_scope();

comment on table public.sowia_agents is
    'Owner-controlled SOW IA agents with explicit permissions to read workspace/project memory.';
comment on table public.sowia_agent_memory_items is
    'Private persistent memory belonging to one owner-controlled SOW IA agent.';
