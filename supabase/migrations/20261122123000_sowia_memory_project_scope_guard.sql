-- Enforce that a project-linked memory belongs to the same owner and workspace.
CREATE OR REPLACE FUNCTION public.sowia_validate_memory_project_scope()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF NEW.project_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM public.sowia_projects AS p
        WHERE p.id = NEW.project_id
          AND p.user_id = NEW.user_id
          AND p.workspace_id = NEW.workspace_id
          AND p.archived_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Memory project must belong to the same active owner and workspace.'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.sowia_validate_memory_project_scope() FROM PUBLIC, anon, authenticated;

DROP TRIGGER IF EXISTS sowia_memory_project_scope_guard ON public.sowia_memory_items;
CREATE TRIGGER sowia_memory_project_scope_guard
BEFORE INSERT OR UPDATE OF project_id, user_id, workspace_id
ON public.sowia_memory_items
FOR EACH ROW
EXECUTE FUNCTION public.sowia_validate_memory_project_scope();
