-- SOW IA: private PDF storage and Premium entitlement schema.
-- Safe to run more than once. Existing memory/message tables are untouched.

-- Private document bucket: 10 MiB maximum, PDF only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'sowia-private-documents',
    'sowia-private-documents',
    false,
    10485760,
    array['application/pdf']
)
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['application/pdf'];

-- Each object must be stored under the authenticated user's UUID prefix:
-- <auth.uid()>/<generated-filename>.pdf
drop policy if exists "SOW IA users can read their own documents" on storage.objects;
create policy "SOW IA users can read their own documents"
    on storage.objects for select to authenticated
    using (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "SOW IA users can upload their own documents" on storage.objects;
create policy "SOW IA users can upload their own documents"
    on storage.objects for insert to authenticated
    with check (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

drop policy if exists "SOW IA users can delete their own documents" on storage.objects;
create policy "SOW IA users can delete their own documents"
    on storage.objects for delete to authenticated
    using (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );

-- Premium status is written only by the trusted server using the service-role key.
-- Authenticated users may read their own entitlement, but cannot grant themselves access.
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

drop policy if exists "Users can read their own SOW IA entitlement" on public.sowia_entitlements;
create policy "Users can read their own SOW IA entitlement"
    on public.sowia_entitlements for select to authenticated
    using ((select auth.uid()) = user_id);

grant select on public.sowia_entitlements to authenticated;
