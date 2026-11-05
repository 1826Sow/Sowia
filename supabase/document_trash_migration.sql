-- SOW IA document recycle bin. Run once in Supabase SQL Editor.
-- Keeps existing owner-scoped RLS policies; no new access policy is introduced.
alter table public.sowia_documents
    add column if not exists deleted_at timestamptz;

create index if not exists sowia_documents_user_deleted_idx
    on public.sowia_documents (user_id, deleted_at, created_at desc);
