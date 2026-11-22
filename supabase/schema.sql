-- SOW IA cloud data schema
-- Run this in Supabase SQL Editor after creating a project.
-- Row Level Security is mandatory: the app uses the user's Supabase JWT.

create table if not exists public.sowia_messages (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    session_id text not null,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create index if not exists sowia_messages_user_session_idx
    on public.sowia_messages (user_id, session_id, id);

create table if not exists public.sowia_memory_items (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    content text not null,
    category text not null default 'general',
    importance smallint not null default 3,
    tags text[] not null default '{}'::text[],
    source text not null default 'user',
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    archived_at timestamptz,
    constraint sowia_memory_items_content_check
        check (char_length(content) between 1 and 20000),
    constraint sowia_memory_items_category_check
        check (category in ('general','profile','preference','project','decision','technical','workflow','reference','agent')),
    constraint sowia_memory_items_importance_check
        check (importance between 1 and 5),
    constraint sowia_memory_items_source_check
        check (source in ('user','conversation','project','document','system')),
    constraint sowia_memory_items_metadata_object_check
        check (jsonb_typeof(metadata) = 'object')
);

create index if not exists sowia_memory_user_created_idx
    on public.sowia_memory_items (user_id, created_at desc);

create index if not exists sowia_memory_items_search_idx
    on public.sowia_memory_items using gin (to_tsvector('simple', content))
    where archived_at is null;

create index if not exists sowia_messages_search_idx
    on public.sowia_messages using gin (to_tsvector('simple', content));

alter table public.sowia_messages enable row level security;
alter table public.sowia_memory_items enable row level security;

drop policy if exists "Users can read own messages" on public.sowia_messages;
create policy "Users can read own messages"
    on public.sowia_messages for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can add own messages" on public.sowia_messages;
create policy "Users can add own messages"
    on public.sowia_messages for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own messages" on public.sowia_messages;
create policy "Users can delete own messages"
    on public.sowia_messages for delete to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own memory" on public.sowia_memory_items;
create policy "Users can read own memory"
    on public.sowia_memory_items for select to authenticated
    using ((select auth.uid()) = user_id);

drop policy if exists "Users can add own memory" on public.sowia_memory_items;
create policy "Users can add own memory"
    on public.sowia_memory_items for insert to authenticated
    with check ((select auth.uid()) = user_id);

drop policy if exists "Users can delete own memory" on public.sowia_memory_items;
create policy "Users can delete own memory"
    on public.sowia_memory_items for delete to authenticated
    using ((select auth.uid()) = user_id);

grant select, insert, delete on public.sowia_messages to authenticated;
grant select, insert, delete on public.sowia_memory_items to authenticated;
grant usage, select on all sequences in schema public to authenticated;


-- Premium access is written only by the trusted server using the service-role
-- key after PayPal has confirmed a completed capture. Authenticated users may
-- read only their own entitlement; they cannot grant or edit their own access.
create table if not exists public.sowia_entitlements (
    user_id uuid primary key references auth.users(id) on delete cascade,
    status text not null check (status in ('active', 'inactive')),
    provider text not null check (provider in ('paypal')),
    paypal_order_id text not null unique,
    amount numeric(10, 2) not null check (amount > 0),
    currency text not null check (currency = 'EUR'),
    updated_at timestamptz not null default now()
);

alter table public.sowia_entitlements enable row level security;

drop policy if exists "Users can read own Premium entitlement" on public.sowia_entitlements;
create policy "Users can read own Premium entitlement"
    on public.sowia_entitlements for select to authenticated
    using ((select auth.uid()) = user_id);

grant select on public.sowia_entitlements to authenticated;
