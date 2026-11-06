-- SOW IA: optional private PDF storage and Premium entitlement tables.
-- This is an ADDITIVE setup script. It does not alter authentication providers,
-- OAuth URLs, API keys, or existing memory/history tables.
-- Review and run manually in Supabase SQL Editor only when enabling these features.

-- 1) Private PDF bucket (10 MiB maximum; PDF only).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'sowia-private-documents',
    'sowia-private-documents',
    false,
    10485760,
    array['application/pdf']
)
-- Do not alter an existing bucket automatically: inspect its current use and
-- configuration first. A pre-existing bucket with mismatched settings must be
-- handled manually in the isolated test project after review.
on conflict (id) do nothing;

-- Restrictive guard: legacy permissive policies cannot grant cross-user access.
drop policy if exists "SOW IA enforce private PDF folder isolation" on storage.objects;
create policy "SOW IA enforce private PDF folder isolation"
on storage.objects as restrictive for all to public
using (
    bucket_id <> 'sowia-private-documents'
    or (storage.foldername(name))[1] = (select auth.uid())::text
)
with check (
    bucket_id <> 'sowia-private-documents'
    or (storage.foldername(name))[1] = (select auth.uid())::text
);

-- A user's files must be stored under a first-level folder named with auth.uid().
drop policy if exists "SOW IA users read own private PDFs" on storage.objects;
create policy "SOW IA users read own private PDFs"
on storage.objects for select to authenticated
using (
    bucket_id = 'sowia-private-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "SOW IA users upload own private PDFs" on storage.objects;
create policy "SOW IA users upload own private PDFs"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'sowia-private-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "SOW IA users update own private PDFs" on storage.objects;
create policy "SOW IA users update own private PDFs"
on storage.objects for update to authenticated
using (
    bucket_id = 'sowia-private-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
)
with check (
    bucket_id = 'sowia-private-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "SOW IA users delete own private PDFs" on storage.objects;
create policy "SOW IA users delete own private PDFs"
on storage.objects for delete to authenticated
using (
    bucket_id = 'sowia-private-documents'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

-- 2) Premium entitlements. Only the trusted server (service role) should write.
create table if not exists public.sowia_entitlements (
    user_id uuid primary key references auth.users(id) on delete cascade,
    status text not null check (status in ('active', 'inactive', 'cancelled')),
    provider text not null check (provider in ('paypal')),
    paypal_order_id text not null unique,
    amount numeric(10, 2) not null check (amount > 0),
    currency text not null check (currency = 'EUR'),
    updated_at timestamptz not null default now()
);

alter table public.sowia_entitlements enable row level security;

-- Remove the earlier optional-script name too, so upgrades do not leave a duplicate permissive policy.
drop policy if exists "SOW IA users read own Premium entitlement" on public.sowia_entitlements;
drop policy if exists "Users can read own Premium entitlement" on public.sowia_entitlements;
create policy "Users can read own Premium entitlement"
on public.sowia_entitlements for select to authenticated
using ((select auth.uid()) = user_id);

revoke all on public.sowia_entitlements from public, anon, authenticated;
grant select on public.sowia_entitlements to authenticated;

-- No INSERT/UPDATE/DELETE policy is granted to authenticated users.
-- premium_access.py writes with the server-only service-role client after
-- validating the PayPal order on the server.
