-- SOW IA cloud data schema
-- Run this script in Supabase SQL Editor. Safe to re-run.
-- User data is protected by Row Level Security (RLS).

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
    content text not null check (char_length(content) between 1 and 1000),
    created_at timestamptz not null default now()
);
create index if not exists sowia_memory_user_created_idx
    on public.sowia_memory_items (user_id, created_at desc);

alter table public.sowia_messages enable row level security;
alter table public.sowia_memory_items enable row level security;

drop policy if exists "Users can read own messages" on public.sowia_messages;
create policy "Users can read own messages" on public.sowia_messages
    for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "Users can add own messages" on public.sowia_messages;
create policy "Users can add own messages" on public.sowia_messages
    for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "Users can delete own messages" on public.sowia_messages;
create policy "Users can delete own messages" on public.sowia_messages
    for delete to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "Users can read own memory" on public.sowia_memory_items;
create policy "Users can read own memory" on public.sowia_memory_items
    for select to authenticated using ((select auth.uid()) = user_id);
drop policy if exists "Users can add own memory" on public.sowia_memory_items;
create policy "Users can add own memory" on public.sowia_memory_items
    for insert to authenticated with check ((select auth.uid()) = user_id);
drop policy if exists "Users can delete own memory" on public.sowia_memory_items;
create policy "Users can delete own memory" on public.sowia_memory_items
    for delete to authenticated using ((select auth.uid()) = user_id);

grant select, insert, delete on public.sowia_messages to authenticated;
grant select, insert, delete on public.sowia_memory_items to authenticated;
grant usage, select on all sequences in schema public to authenticated;

-- Premium entitlements are readable by their owner only. Writes are reserved
-- for the trusted server using the service-role key after verified capture.
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
create policy "Users can read own Premium entitlement" on public.sowia_entitlements
    for select to authenticated using ((select auth.uid()) = user_id);
grant select on public.sowia_entitlements to authenticated;

-- Private PDF bucket. Storage objects are isolated by the first path segment,
-- which the app sets to the authenticated user's UUID.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('sowia-private-documents', 'sowia-private-documents', false, 10485760, array['application/pdf'])
on conflict (id) do update set
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "SOW IA users read own PDFs" on storage.objects;
create policy "SOW IA users read own PDFs" on storage.objects
    for select to authenticated
    using (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "SOW IA users upload own PDFs" on storage.objects;
create policy "SOW IA users upload own PDFs" on storage.objects
    for insert to authenticated
    with check (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "SOW IA users delete own PDFs" on storage.objects;
create policy "SOW IA users delete own PDFs" on storage.objects
    for delete to authenticated
    using (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
