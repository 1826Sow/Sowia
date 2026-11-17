-- Independent, persistent conversation registry for SOW IA.
-- Existing sowia_messages rows are deliberately preserved; legacy sessions
-- are registered lazily when their owner opens the Assistant IA.
create table if not exists public.sowia_conversations (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'personal'
        check (workspace_id in ('personal', 'professional')),
    session_id text not null check (char_length(session_id) between 1 and 128),
    title text not null default 'Nouvelle conversation'
        check (char_length(title) between 1 and 100),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, workspace_id, session_id)
);

create index if not exists sowia_conversations_owner_workspace_updated_idx
    on public.sowia_conversations (user_id, workspace_id, updated_at desc);

alter table public.sowia_conversations enable row level security;

drop policy if exists "Users can read own SOW IA conversations" on public.sowia_conversations;
create policy "Users can read own SOW IA conversations"
    on public.sowia_conversations for select to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can create own SOW IA conversations" on public.sowia_conversations;
create policy "Users can create own SOW IA conversations"
    on public.sowia_conversations for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

drop policy if exists "Users can update own SOW IA conversations" on public.sowia_conversations;
create policy "Users can update own SOW IA conversations"
    on public.sowia_conversations for update to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    )
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

grant select, insert, update on public.sowia_conversations to authenticated;
grant usage, select on sequence public.sowia_conversations_id_seq to authenticated;
