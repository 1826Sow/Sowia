-- Migration for existing SOW IA Supabase installations.
-- Run once in Supabase SQL Editor to enable virtual folders.
alter table public.sowia_documents
    add column if not exists folder text not null default 'Général';

alter table public.sowia_documents
    drop constraint if exists sowia_documents_folder_check;

alter table public.sowia_documents
    add constraint sowia_documents_folder_check
    check (char_length(folder) between 1 and 60);

-- The existing owner-scoped UPDATE policy from document_library.sql
-- protects folder changes. No new policy or broader access is introduced.
