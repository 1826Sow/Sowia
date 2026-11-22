-- Cover the project_id foreign key with a leading-column index.
CREATE INDEX IF NOT EXISTS sowia_memory_items_project_fk_idx
    ON public.sowia_memory_items (project_id)
    WHERE project_id IS NOT NULL;
