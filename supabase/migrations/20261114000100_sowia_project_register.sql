-- Persistent, account-scoped project register for the SOW IA Executive Hub.
-- Additive migration: existing conversations and documents are not modified.
create table if not exists public.sowia_projects (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'personal'
        check (workspace_id in ('personal', 'professional')),
    title text not null check (char_length(title) between 1 and 160),
    description text not null default '' check (char_length(description) <= 4000),
    status text not null default 'En cours'
        check (status in ('En cours', 'À tester', 'Validé', 'Terminé')),
    conversation_session_id text,
    deliverables jsonb not null default '[]'::jsonb
        check (jsonb_typeof(deliverables) = 'array'),
    metadata jsonb not null default '{}'::jsonb
        check (jsonb_typeof(metadata) = 'object'),
    archived_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sowia_projects_owner_workspace_updated_idx
    on public.sowia_projects (user_id, workspace_id, updated_at desc);
create index if not exists sowia_projects_owner_workspace_status_idx
    on public.sowia_projects (user_id, workspace_id, status, updated_at desc);

alter table public.sowia_projects enable row level security;

drop policy if exists "Users can read own SOW IA projects" on public.sowia_projects;
create policy "Users can read own SOW IA projects"
    on public.sowia_projects for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can create own SOW IA projects" on public.sowia_projects;
create policy "Users can create own SOW IA projects"
    on public.sowia_projects for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can update own SOW IA projects" on public.sowia_projects;
create policy "Users can update own SOW IA projects"
    on public.sowia_projects for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

grant select, insert, update on public.sowia_projects to authenticated;
grant usage, select on sequence public.sowia_projects_id_seq to authenticated;
