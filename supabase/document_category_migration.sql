-- Migration for existing SOW IA installations.
-- Run once in Supabase SQL Editor to enable persistent editable categories.
alter table public.sowia_documents
    add column if not exists category text not null default 'Autres';

alter table public.sowia_documents
    drop constraint if exists sowia_documents_category_check;

alter table public.sowia_documents
    add constraint sowia_documents_category_check
    check (category in ('Finances', 'Administratif', 'Travail', 'Études', 'Santé', 'Autres'));

drop policy if exists "Users can update their own SOW IA document categories" on public.sowia_documents;
create policy "Users can update their own SOW IA document categories"
    on public.sowia_documents for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

grant select, insert, update, delete on public.sowia_documents to authenticated;
