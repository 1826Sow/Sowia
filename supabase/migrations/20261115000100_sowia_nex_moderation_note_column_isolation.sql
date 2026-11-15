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

-- Fail atomically if the intended privilege boundary was not achieved.
DO $verification$
BEGIN
    IF has_table_privilege(
        'authenticated',
        'public.sowia_night_exchange_apps',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'authenticated still has table-level SELECT';
    END IF;

    IF has_column_privilege(
        'authenticated',
        'public.sowia_night_exchange_apps',
        'moderation_note',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'authenticated can still read moderation_note';
    END IF;

    IF NOT has_column_privilege(
        'authenticated',
        'public.sowia_night_exchange_apps',
        'status',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'authenticated lost required SELECT on status';
    END IF;

    IF has_any_column_privilege(
        'anon',
        'public.sowia_night_exchange_apps',
        'SELECT'
    ) THEN
        RAISE EXCEPTION 'anon unexpectedly has SELECT on NIGHT EXCHANGE apps';
    END IF;
END;
$verification$;

COMMIT;
