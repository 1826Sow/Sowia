-- Cover the project foreign key for efficient project updates/deletes.
create index if not exists sowia_memory_items_project_id_idx
    on public.sowia_memory_items (project_id)
    where project_id is not null;
