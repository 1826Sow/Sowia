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
