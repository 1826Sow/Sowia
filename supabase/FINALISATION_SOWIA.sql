-- SOW IA — script SQL de finalisation Supabase
-- À exécuter une seule fois dans Supabase > SQL Editor, après sauvegarde.
-- Regroupe le schéma des espaces, la sécurité du stockage PDF et les abonnements PayPal.
-- Ce script configure la base uniquement : il ne déploie pas la fonction Edge ni n'active les paiements.

-- ================================================================
-- 1. SCHÉMA CLOUD ET ISOLATION DES ESPACES
-- ================================================================
-- SOW IA cloud data schema
-- Run this in Supabase SQL Editor after creating a project.
-- Row Level Security is mandatory: the app uses the user's Supabase JWT.

create table if not exists public.sowia_messages (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    session_id text not null,
    workspace_id text not null default 'personal'
        constraint sowia_messages_workspace_id_check check (workspace_id in ('personal', 'professional')),
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

alter table public.sowia_messages
    add column if not exists workspace_id text;
update public.sowia_messages set workspace_id = 'personal' where workspace_id is null;
alter table public.sowia_messages
    alter column workspace_id set default 'personal',
    alter column workspace_id set not null;

do $block$ begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'sowia_messages_workspace_id_check'
          and conrelid = 'public.sowia_messages'::regclass
    ) then
        alter table public.sowia_messages
            add constraint sowia_messages_workspace_id_check
            check (workspace_id in ('personal', 'professional'));
    end if;
end $block$;

create index if not exists sowia_messages_user_workspace_session_idx
    on public.sowia_messages (user_id, workspace_id, session_id, id);

create table if not exists public.sowia_memory_items (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'personal'
        constraint sowia_memory_items_workspace_id_check check (workspace_id in ('personal', 'professional')),
    content text not null check (char_length(content) between 1 and 1000),
    created_at timestamptz not null default now()
);

alter table public.sowia_memory_items
    add column if not exists workspace_id text;
update public.sowia_memory_items set workspace_id = 'personal' where workspace_id is null;
alter table public.sowia_memory_items
    alter column workspace_id set default 'personal',
    alter column workspace_id set not null;

do $block$ begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'sowia_memory_items_workspace_id_check'
          and conrelid = 'public.sowia_memory_items'::regclass
    ) then
        alter table public.sowia_memory_items
            add constraint sowia_memory_items_workspace_id_check
            check (workspace_id in ('personal', 'professional'));
    end if;
end $block$;

create index if not exists sowia_memory_user_workspace_created_idx
    on public.sowia_memory_items (user_id, workspace_id, created_at desc);

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


-- ================================================================
-- 2. BUCKET PDF PRIVÉ ET POLITIQUES STORAGE
-- ================================================================
-- SOW IA private PDF bucket and per-user Storage policies.
-- Run after schema.sql in the Supabase SQL Editor.
-- This script is safe to re-run and keeps the dedicated bucket private.

insert into storage.buckets (
    id, name, public, file_size_limit, allowed_mime_types
)
values (
    'sowia-files',
    'sowia-files',
    false,
    10485760,
    array['application/pdf']::text[]
)
on conflict (id) do update
set
    name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "SOW IA users can read own files" on storage.objects;
create policy "SOW IA users can read own files"
    on storage.objects
    for select
    to authenticated
    using (
        bucket_id = 'sowia-files'
        and (storage.foldername(name))[1] = (select auth.uid()::text)
    );

drop policy if exists "SOW IA users can upload own files" on storage.objects;
create policy "SOW IA users can upload own files"
    on storage.objects
    for insert
    to authenticated
    with check (
        bucket_id = 'sowia-files'
        and (storage.foldername(name))[1] = (select auth.uid()::text)
    );

drop policy if exists "SOW IA users can delete own files" on storage.objects;
create policy "SOW IA users can delete own files"
    on storage.objects
    for delete
    to authenticated
    using (
        bucket_id = 'sowia-files'
        and (storage.foldername(name))[1] = (select auth.uid()::text)
    );


-- ================================================================
-- 3. TABLE DES ABONNEMENTS PAYPAL
-- ================================================================
-- SOW IA recurring PayPal subscriptions.
-- Apply this migration in Supabase before deploying the paypal-webhook Edge Function.
create table if not exists public.sowia_subscriptions (
    id bigint generated by default as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    provider text not null default 'paypal' check (provider = 'paypal'),
    paypal_subscription_id text not null unique,
    paypal_plan_id text not null,
    status text not null,
    currency text,
    amount numeric(12, 2),
    next_billing_time timestamptz,
    last_payment_at timestamptz,
    updated_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists sowia_subscriptions_user_status_idx
    on public.sowia_subscriptions (user_id, status);

-- Keep at most one active recurring subscription per SOW IA account.
create unique index if not exists sowia_subscriptions_one_active_per_user_idx
    on public.sowia_subscriptions (user_id)
    where status = 'active';

alter table public.sowia_subscriptions enable row level security;

drop policy if exists "Users can read their own SOW IA subscription"
    on public.sowia_subscriptions;

create policy "Users can read their own SOW IA subscription"
    on public.sowia_subscriptions
    for select
    to authenticated
    using (auth.uid() = user_id);

-- No client INSERT/UPDATE/DELETE policies are intentionally created.
-- Only the Supabase service-role Edge Function may write subscription state.


-- FIN : vérifier ensuite les règles RLS avec deux comptes de test.
-- Ne pas activer SOWIA_SUBSCRIPTIONS_ENABLED avant le déploiement et les tests Sandbox.