-- SOW IA: private PDF bucket with per-user folder isolation.
-- Apply once in Supabase SQL Editor. Safe to re-run.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'sowia-private-documents',
    'sowia-private-documents',
    false,
    10485760,
    array['application/pdf']::text[]
)
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['application/pdf']::text[];

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

drop policy if exists "SOW IA users delete own private PDFs" on storage.objects;
create policy "SOW IA users delete own private PDFs"
    on storage.objects for delete to authenticated
    using (
        bucket_id = 'sowia-private-documents'
        and (storage.foldername(name))[1] = (select auth.uid())::text
    );
