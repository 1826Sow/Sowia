-- Durable, per-agent conversation history.
-- Additive only: existing SOW IA conversations and messages are untouched.

create table if not exists public.sowia_agent_conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    agent_id uuid not null references public.sowia_agents(id) on delete cascade,
    workspace_id text not null check (workspace_id in ('personal', 'professional')),
    title text not null default 'Nouvelle conversation'
        check (char_length(title) between 1 and 100),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sowia_agent_conversations_owner_agent_unique
        unique (id, user_id, agent_id, workspace_id)
);

create index if not exists sowia_agent_conversations_owner_agent_updated_idx
    on public.sowia_agent_conversations
       (user_id, workspace_id, agent_id, updated_at desc);

alter table public.sowia_agent_conversations enable row level security;

drop policy if exists sowia_agent_conversations_select_own
    on public.sowia_agent_conversations;
create policy sowia_agent_conversations_select_own
    on public.sowia_agent_conversations for select to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_conversations.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_conversations.workspace_id
        )
    );

drop policy if exists sowia_agent_conversations_insert_own
    on public.sowia_agent_conversations;
create policy sowia_agent_conversations_insert_own
    on public.sowia_agent_conversations for insert to authenticated
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_conversations.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_conversations.workspace_id
              and a.status = 'active'
        )
    );

drop policy if exists sowia_agent_conversations_update_own
    on public.sowia_agent_conversations;
create policy sowia_agent_conversations_update_own
    on public.sowia_agent_conversations for update to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_conversations.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_conversations.workspace_id
        )
    )
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agents a
            where a.id = sowia_agent_conversations.agent_id
              and a.user_id = (select auth.uid())
              and a.workspace_id = sowia_agent_conversations.workspace_id
        )
    );

grant select, insert, update on public.sowia_agent_conversations to authenticated;

create table if not exists public.sowia_agent_messages (
    id bigint generated always as identity primary key,
    conversation_id uuid not null,
    user_id uuid not null references auth.users(id) on delete cascade,
    agent_id uuid not null references public.sowia_agents(id) on delete cascade,
    workspace_id text not null check (workspace_id in ('personal', 'professional')),
    role text not null check (role in ('user', 'assistant')),
    content text not null check (char_length(content) between 1 and 24000),
    created_at timestamptz not null default now(),
    constraint sowia_agent_messages_conversation_scope_fk
        foreign key (conversation_id, user_id, agent_id, workspace_id)
        references public.sowia_agent_conversations(id, user_id, agent_id, workspace_id)
        on delete cascade
);

create index if not exists sowia_agent_messages_conversation_order_idx
    on public.sowia_agent_messages (conversation_id, id);

alter table public.sowia_agent_messages enable row level security;

drop policy if exists sowia_agent_messages_select_own
    on public.sowia_agent_messages;
create policy sowia_agent_messages_select_own
    on public.sowia_agent_messages for select to authenticated
    using (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1 from public.sowia_agent_conversations c
            where c.id = sowia_agent_messages.conversation_id
              and c.user_id = (select auth.uid())
              and c.agent_id = sowia_agent_messages.agent_id
              and c.workspace_id = sowia_agent_messages.workspace_id
        )
    );

drop policy if exists sowia_agent_messages_insert_own
    on public.sowia_agent_messages;
create policy sowia_agent_messages_insert_own
    on public.sowia_agent_messages for insert to authenticated
    with check (
        user_id = (select auth.uid())
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and exists (
            select 1
            from public.sowia_agent_conversations c
            join public.sowia_agents a
              on a.id = c.agent_id
             and a.user_id = c.user_id
             and a.workspace_id = c.workspace_id
            where c.id = sowia_agent_messages.conversation_id
              and c.user_id = (select auth.uid())
              and c.agent_id = sowia_agent_messages.agent_id
              and c.workspace_id = sowia_agent_messages.workspace_id
              and a.status = 'active'
        )
    );

grant select, insert on public.sowia_agent_messages to authenticated;
grant usage, select on sequence public.sowia_agent_messages_id_seq to authenticated;

comment on table public.sowia_agent_conversations is
    'Durable conversation threads owned by one SOW IA user and one of their agents.';
comment on table public.sowia_agent_messages is
    'Durable user/assistant messages scoped to an owned SOW IA agent conversation.';
