-- SOW IA private document library.
-- Run once in Supabase SQL Editor. The bucket is private; no public URLs are created.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'sowia-files',
    'sowia-files',
    false,
    10485760,
    array['application/pdf']
)
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['application/pdf'];

drop policy if exists "SOW IA users read own documents" on storage.objects;
create policy "SOW IA users read own documents"
on storage.objects for select to authenticated
using (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "SOW IA users upload own documents" on storage.objects;
create policy "SOW IA users upload own documents"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);

drop policy if exists "SOW IA users delete own documents" on storage.objects;
create policy "SOW IA users delete own documents"
on storage.objects for delete to authenticated
using (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
);
