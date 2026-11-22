-- SOW IA durable memory expansion and cross-conversation retrieval.
-- Additive only: existing memory notes and messages are preserved.
ALTER TABLE public.sowia_memory_items
    ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT 'general',
    ADD COLUMN IF NOT EXISTS importance smallint NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}'::text[],
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS project_id bigint,
    ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS archived_at timestamptz;

ALTER TABLE public.sowia_memory_items
    DROP CONSTRAINT IF EXISTS sowia_memory_items_content_check;

ALTER TABLE public.sowia_memory_items
    ADD CONSTRAINT sowia_memory_items_content_check
        CHECK (char_length(content) BETWEEN 1 AND 20000),
    ADD CONSTRAINT sowia_memory_items_category_check
        CHECK (category IN ('general','profile','preference','project','decision','technical','workflow','reference','agent')),
    ADD CONSTRAINT sowia_memory_items_importance_check
        CHECK (importance BETWEEN 1 AND 5),
    ADD CONSTRAINT sowia_memory_items_source_check
        CHECK (source IN ('user','conversation','project','document','system')),
    ADD CONSTRAINT sowia_memory_items_metadata_object_check
        CHECK (jsonb_typeof(metadata) = 'object');

DO $$
BEGIN
    IF to_regclass('public.sowia_projects') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
           WHERE conname = 'sowia_memory_items_project_id_fkey'
             AND conrelid = 'public.sowia_memory_items'::regclass
       ) THEN
        ALTER TABLE public.sowia_memory_items
            ADD CONSTRAINT sowia_memory_items_project_id_fkey
            FOREIGN KEY (project_id)
            REFERENCES public.sowia_projects(id)
            ON DELETE SET NULL;
    END IF;
END;
$$;

UPDATE public.sowia_memory_items
SET updated_at = created_at
WHERE updated_at IS DISTINCT FROM created_at;

CREATE INDEX IF NOT EXISTS sowia_memory_items_owner_workspace_priority_idx
    ON public.sowia_memory_items (user_id, workspace_id, importance DESC, updated_at DESC)
    WHERE archived_at IS NULL;

CREATE INDEX IF NOT EXISTS sowia_memory_items_project_idx
    ON public.sowia_memory_items (user_id, workspace_id, project_id)
    WHERE project_id IS NOT NULL AND archived_at IS NULL;

CREATE INDEX IF NOT EXISTS sowia_memory_items_search_idx
    ON public.sowia_memory_items
    USING gin (to_tsvector('simple', content))
    WHERE archived_at IS NULL;

CREATE INDEX IF NOT EXISTS sowia_messages_search_idx
    ON public.sowia_messages
    USING gin (to_tsvector('simple', content));

CREATE INDEX IF NOT EXISTS sowia_messages_owner_workspace_created_idx
    ON public.sowia_messages (user_id, workspace_id, created_at DESC);

ALTER TABLE public.sowia_memory_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Restrict SOW IA memories to owner" ON public.sowia_memory_items;
CREATE POLICY "Restrict SOW IA memories to owner"
    ON public.sowia_memory_items
    AS RESTRICTIVE
    FOR ALL
    TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE OR REPLACE FUNCTION public.sowia_search_memory_context(
    p_workspace_id text,
    p_query text,
    p_exclude_session_id text DEFAULT NULL,
    p_project_id bigint DEFAULT NULL,
    p_match_count integer DEFAULT 80
)
RETURNS TABLE (
    source_type text,
    source_id text,
    content text,
    created_at timestamptz,
    category text,
    importance smallint,
    tags text[],
    session_id text,
    project_id bigint
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
    WITH query_input AS (
        SELECT
            NULLIF(BTRIM(p_query), '') AS query_text,
            websearch_to_tsquery('simple', COALESCE(NULLIF(BTRIM(p_query), ''), '')) AS tsq
    ),
    memory_hits AS (
        SELECT
            m.source::text AS source_type,
            m.id::text AS source_id,
            m.content,
            m.created_at,
            m.category,
            m.importance,
            m.tags,
            NULL::text AS session_id,
            m.project_id,
            CASE
                WHEN q.query_text IS NULL OR numnode(q.tsq) = 0 THEN 0.0
                ELSE ts_rank_cd(to_tsvector('simple', m.content), q.tsq)
            END AS relevance
        FROM public.sowia_memory_items AS m
        CROSS JOIN query_input AS q
        WHERE m.user_id = (SELECT auth.uid())
          AND m.workspace_id = p_workspace_id
          AND p_workspace_id IN ('personal', 'professional')
          AND (p_project_id IS NULL OR m.project_id IS NULL OR m.project_id = p_project_id)
          AND m.archived_at IS NULL
          AND (
              q.query_text IS NULL
              OR numnode(q.tsq) = 0
              OR to_tsvector('simple', m.content) @@ q.tsq
          )
    ),
    conversation_hits AS (
        SELECT
            ('conversation_' || m.role)::text AS source_type,
            m.id::text AS source_id,
            m.content,
            m.created_at,
            'conversation'::text AS category,
            CASE WHEN m.role = 'user' THEN 3 ELSE 1 END::smallint AS importance,
            '{}'::text[] AS tags,
            m.session_id,
            NULL::bigint AS project_id,
            ts_rank_cd(to_tsvector('simple', m.content), q.tsq) AS relevance
        FROM public.sowia_messages AS m
        CROSS JOIN query_input AS q
        WHERE m.user_id = (SELECT auth.uid())
          AND m.workspace_id = p_workspace_id
          AND p_workspace_id IN ('personal', 'professional')
          AND m.session_id IS DISTINCT FROM p_exclude_session_id
          AND q.query_text IS NOT NULL
          AND numnode(q.tsq) > 0
          AND to_tsvector('simple', m.content) @@ q.tsq
    )
    SELECT
        results.source_type,
        results.source_id,
        results.content,
        results.created_at,
        results.category,
        results.importance,
        results.tags,
        results.session_id,
        results.project_id
    FROM (
        SELECT * FROM memory_hits
        UNION ALL
        SELECT * FROM conversation_hits
    ) AS results
    ORDER BY results.relevance DESC, results.importance DESC, results.created_at DESC
    LIMIT LEAST(GREATEST(COALESCE(p_match_count, 80), 1), 100);
$$;

REVOKE ALL ON FUNCTION public.sowia_search_memory_context(text, text, text, bigint, integer)
    FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.sowia_search_memory_context(text, text, text, bigint, integer)
    TO authenticated;

GRANT SELECT, INSERT, DELETE ON public.sowia_memory_items TO authenticated;
