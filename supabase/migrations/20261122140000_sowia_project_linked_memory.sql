-- Add project-aware memory links without rewriting or deleting existing notes.
-- A removed project detaches its notes instead of deleting user memory.
alter table public.sowia_memory_items
    add column if not exists project_id bigint;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conrelid = 'public.sowia_memory_items'::regclass
          and conname = 'sowia_memory_items_project_id_fkey'
    ) then
        alter table public.sowia_memory_items
            add constraint sowia_memory_items_project_id_fkey
            foreign key (project_id)
            references public.sowia_projects(id)
            on delete set null;
    end if;
end $$;

create index if not exists sowia_memory_items_project_context_idx
    on public.sowia_memory_items (user_id, workspace_id, project_id, created_at desc);

-- A note may only point to a project owned by the same account and workspace.
-- Legacy/general notes remain valid with project_id IS NULL.
drop policy if exists "Users can add their own SOW IA memories" on public.sowia_memory_items;
create policy "Users can add their own SOW IA memories"
    on public.sowia_memory_items for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (
            project_id is null
            or exists (
                select 1
                from public.sowia_projects p
                where p.id = sowia_memory_items.project_id
                  and p.user_id = sowia_memory_items.user_id
                  and p.workspace_id = sowia_memory_items.workspace_id
            )
        )
    );

comment on column public.sowia_memory_items.project_id is
    'Optional project association; NULL denotes a general workspace memory.';
