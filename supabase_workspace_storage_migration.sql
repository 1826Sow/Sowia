-- SOW IA: workspace separation and private PDF storage.
-- Apply this migration before deploying the workspace code.
-- Existing memory and message rows are retained in the Personal workspace.
-- No Premium entitlement table or payment configuration is created here.

begin;

alter table public.sowia_memory_items
    add column if not exists workspace_id text not null default 'personal';
alter table public.sowia_messages
    add column if not exists workspace_id text not null default 'personal';

alter table public.sowia_memory_items
    drop constraint if exists sowia_memory_items_workspace_id_check;
alter table public.sowia_memory_items
    add constraint sowia_memory_items_workspace_id_check
    check (workspace_id in ('personal', 'professional'));

alter table public.sowia_messages
    drop constraint if exists sowia_messages_workspace_id_check;
alter table public.sowia_messages
    add constraint sowia_messages_workspace_id_check
    check (workspace_id in ('personal', 'professional'));

create index if not exists sowia_memory_items_user_workspace_created_idx
    on public.sowia_memory_items (user_id, workspace_id, created_at desc);
create index if not exists sowia_messages_user_workspace_session_idx
    on public.sowia_messages (user_id, workspace_id, session_id, id desc);

-- Private PDF bucket: 10 MiB maximum, PDF only.
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

-- Policies bind every stored object to the authenticated user's UUID.
-- Nested paths are supported: <user_uuid>/<workspace>/<filename>.pdf
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

commit;
