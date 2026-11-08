-- SOW IA: private PDF bucket with per-user and per-workspace access.
-- Safe to run repeatedly. Existing object paths are retained.
-- Legacy files stored as <user_id>/<file.pdf> remain Personal-only.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('sowia-files', 'sowia-files', false, 10485760, array['application/pdf'])
on conflict (id) do update
set public = false,
    file_size_limit = 10485760,
    allowed_mime_types = array['application/pdf'];

-- Remove both current policy names and names from the earlier compatibility
-- script. PostgreSQL permissive policies are combined with OR, so leaving an
-- older broader policy in place would weaken the workspace restrictions below.
drop policy if exists "SOW IA users read own documents" on storage.objects;
drop policy if exists "SOW IA users upload own documents" on storage.objects;
drop policy if exists "SOW IA users delete own documents" on storage.objects;

drop policy if exists "SOW IA users can read own workspace PDFs" on storage.objects;
create policy "SOW IA users can read own workspace PDFs"
on storage.objects for select to authenticated
using (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and (
        array_length(storage.foldername(name), 1) = 1
        or (
            array_length(storage.foldername(name), 1) = 2
            and (storage.foldername(name))[2] in ('personal', 'professional')
        )
    )
);

drop policy if exists "SOW IA users can upload own workspace PDFs" on storage.objects;
create policy "SOW IA users can upload own workspace PDFs"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and array_length(storage.foldername(name), 1) = 2
    and (storage.foldername(name))[2] in ('personal', 'professional')
);

drop policy if exists "SOW IA users can delete own workspace PDFs" on storage.objects;
create policy "SOW IA users can delete own workspace PDFs"
on storage.objects for delete to authenticated
using (
    bucket_id = 'sowia-files'
    and (storage.foldername(name))[1] = (select auth.uid())::text
    and (
        array_length(storage.foldername(name), 1) = 1
        or (
            array_length(storage.foldername(name), 1) = 2
            and (storage.foldername(name))[2] in ('personal', 'professional')
        )
    )
);
