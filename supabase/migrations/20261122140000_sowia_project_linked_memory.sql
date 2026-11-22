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

-- Enforce project ownership and active-project status even if a future policy changes.
create or replace function public.sowia_validate_memory_project_scope()
returns trigger
language plpgsql
set search_path to 'public', 'pg_temp'
as $function$
begin
    if new.project_id is not null and not exists (
        select 1
        from public.sowia_projects as p
        where p.id = new.project_id
          and p.user_id = new.user_id
          and p.workspace_id = new.workspace_id
          and p.archived_at is null
    ) then
        raise exception 'Memory project must belong to the same active owner and workspace.'
            using errcode = '42501';
    end if;
    return new;
end;
$function$;

drop trigger if exists sowia_memory_project_scope_guard on public.sowia_memory_items;
create trigger sowia_memory_project_scope_guard
    before insert or update of project_id, user_id, workspace_id
    on public.sowia_memory_items
    for each row
    execute function public.sowia_validate_memory_project_scope();

-- Replace the table's existing permissive policies as a set. PostgreSQL combines
-- permissive policies with OR, so keeping an older broad INSERT policy would
-- silently bypass the project-scope condition below.
do $$
declare
    existing_policy record;
begin
    for existing_policy in
        select policyname
        from pg_policies
        where schemaname = 'public'
          and tablename = 'sowia_memory_items'
    loop
        execute format(
            'drop policy %I on public.sowia_memory_items',
            existing_policy.policyname
        );
    end loop;
end $$;

create policy "memory_select_own"
    on public.sowia_memory_items for select to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

create policy "memory_insert_own"
    on public.sowia_memory_items for insert to authenticated
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and (
            project_id is null
            or exists (
                select 1
                from public.sowia_projects p
                where p.id = sowia_memory_items.project_id
                  and p.user_id = sowia_memory_items.user_id
                  and p.workspace_id = sowia_memory_items.workspace_id
                  and p.archived_at is null
            )
        )
    );

create policy "memory_update_own"
    on public.sowia_memory_items for update to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    )
    with check (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
        and (
            project_id is null
            or exists (
                select 1
                from public.sowia_projects p
                where p.id = sowia_memory_items.project_id
                  and p.user_id = sowia_memory_items.user_id
                  and p.workspace_id = sowia_memory_items.workspace_id
                  and p.archived_at is null
            )
        )
    );

create policy "memory_delete_own"
    on public.sowia_memory_items for delete to authenticated
    using (
        (select auth.uid()) = user_id
        and (workspace_id = 'personal' or public.sowia_has_professional_access())
    );

comment on column public.sowia_memory_items.project_id is
    'Optional project association; NULL denotes a general workspace memory.';
