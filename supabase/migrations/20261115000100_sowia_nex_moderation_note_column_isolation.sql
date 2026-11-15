-- NIGHT EXCHANGE: isolate moderation notes from direct authenticated table reads.
-- Apply only after the matching cloud_storage.py change is deployed to TEST.
-- The owner-scoped SECURITY DEFINER RPC remains the sole read path for a user's own note.

BEGIN;

REVOKE SELECT
ON TABLE public.sowia_night_exchange_apps
FROM authenticated;

GRANT SELECT (
    id,
    user_id,
    workspace_id,
    app_name,
    country,
    timezone,
    categories,
    services_offered,
    services_wanted,
    night_start,
    night_end,
    status,
    created_at,
    updated_at
)
ON TABLE public.sowia_night_exchange_apps
TO authenticated;

COMMIT;

-- Expected after applying in TEST:
-- has_table_privilege('authenticated', ..., 'SELECT') = false
-- has_column_privilege('authenticated', ..., 'moderation_note', 'SELECT') = false
-- has_column_privilege('authenticated', ..., 'status', 'SELECT') = true
