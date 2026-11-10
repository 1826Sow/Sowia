-- SOW IA: READ-ONLY deployment diagnostic.
-- Run after supabase/schema.sql, supabase_workspaces.sql and
-- supabase_storage_policies.sql in the Supabase SQL Editor.
-- This script only reads PostgreSQL catalog and Storage metadata.

with expected_tables(table_name) as (
    values
        ('sowia_messages'),
        ('sowia_memory_items'),
        ('sowia_entitlements'),
        ('sowia_growth_leads'),
        ('sowia_user_preferences')
),
table_checks as (
    select
        'table'::text as check_type,
        e.table_name::text as object_name,
        case when c.oid is null then 'MISSING' else 'PRESENT' end as status,
        case
            when c.oid is null then 'Table public.' || e.table_name || ' not found'
            else 'RLS enabled=' || c.relrowsecurity::text
                 || '; RLS forced=' || c.relforcerowsecurity::text
        end as detail
    from expected_tables e
    left join pg_class c
        on c.relname = e.table_name
    left join pg_namespace n
        on n.oid = c.relnamespace and n.nspname = 'public'
    where c.oid is null or n.oid is not null
),
expected_columns(table_name, column_name) as (
    values
        ('sowia_messages', 'user_id'),
        ('sowia_messages', 'session_id'),
        ('sowia_messages', 'role'),
        ('sowia_messages', 'content'),
        ('sowia_messages', 'workspace_id'),
        ('sowia_memory_items', 'user_id'),
        ('sowia_memory_items', 'content'),
        ('sowia_memory_items', 'workspace_id'),
        ('sowia_entitlements', 'user_id'),
        ('sowia_entitlements', 'status'),
        ('sowia_entitlements', 'provider'),
        ('sowia_entitlements', 'paypal_order_id'),
        ('sowia_growth_leads', 'user_id'),
        ('sowia_growth_leads', 'workspace_id'),
        ('sowia_growth_leads', 'organization'),
        ('sowia_growth_leads', 'country'),
        ('sowia_growth_leads', 'status'),
        ('sowia_growth_leads', 'source_url'),
        ('sowia_user_preferences', 'user_id'),
        ('sowia_user_preferences', 'language'),
        ('sowia_user_preferences', 'updated_at')
),
column_checks as (
    select
        'column'::text as check_type,
        (e.table_name || '.' || e.column_name)::text as object_name,
        case when c.column_name is null then 'MISSING' else 'PRESENT' end as status,
        coalesce(c.data_type, 'Expected column is absent from public schema')::text as detail
    from expected_columns e
    left join information_schema.columns c
        on c.table_schema = 'public'
       and c.table_name = e.table_name
       and c.column_name = e.column_name
)
select check_type, object_name, status, detail from table_checks
union all
select check_type, object_name, status, detail from column_checks
union all
select
    'table RLS policy'::text,
    schemaname || '.' || tablename || ' / ' || policyname,
    cmd::text,
    'roles=' || coalesce(roles::text, '<null>')
        || '; USING=' || coalesce(qual, '<none>')
        || '; WITH CHECK=' || coalesce(with_check, '<none>')
from pg_policies
where schemaname = 'public'
  and tablename in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements', 'sowia_growth_leads', 'sowia_user_preferences')
union all
select
    'storage bucket'::text,
    id::text,
    case when public then 'PUBLIC - CHECK' else 'PRIVATE' end,
    'file_size_limit=' || coalesce(file_size_limit::text, '<null>')
        || '; allowed_mime_types=' || coalesce(allowed_mime_types::text, '<null>')
from storage.buckets
where id = 'sowia-files'
union all
select
    'storage.objects policy'::text,
    policyname::text,
    cmd::text,
    'roles=' || coalesce(roles::text, '<null>')
        || '; USING=' || coalesce(qual, '<none>')
        || '; WITH CHECK=' || coalesce(with_check, '<none>')
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
order by check_type, object_name;
