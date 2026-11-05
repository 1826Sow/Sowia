-- SOW IA: read-only post-migration security verification.
-- Run in Supabase SQL Editor AFTER applying the documented migrations.
-- This script only reads PostgreSQL catalog metadata; it changes no data or schema.

with expected_columns(table_name, column_name) as (
    values
        ('sowia_documents', 'user_id'),
        ('sowia_documents', 'created_at'),
        ('sowia_documents', 'category'),
        ('sowia_documents', 'folder'),
        ('sowia_documents', 'deleted_at'),
        ('sowia_comparison_history', 'user_id'),
        ('sowia_comparison_history', 'report'),
        ('sowia_comparison_history', 'created_at')
),
column_checks as (
    select
        'Colonne ' || c.table_name || '.' || c.column_name as check_name,
        case when exists (
            select 1
            from information_schema.columns ic
            where ic.table_schema = 'public'
              and ic.table_name = c.table_name
              and ic.column_name = c.column_name
        ) then 'OK' else 'À CORRIGER' end as status,
        'Vérification de présence dans public.' || c.table_name as details
    from expected_columns c
),
expected_tables(table_name) as (
    values ('sowia_documents'), ('sowia_comparison_history')
),
table_checks as (
    select
        'Table public.' || t.table_name as check_name,
        case when to_regclass('public.' || t.table_name) is not null
            then 'OK' else 'TABLE ABSENTE' end as status,
        'La table doit exister pour les fonctions cloud concernées.' as details
    from expected_tables t
),
rls_checks as (
    select
        'RLS public.' || t.table_name as check_name,
        case when coalesce((
            select cls.relrowsecurity
            from pg_class cls
            join pg_namespace ns on ns.oid = cls.relnamespace
            where ns.nspname = 'public' and cls.relname = t.table_name
        ), false) then 'OK' else 'À CORRIGER' end as status,
        'RLS doit être activé.' as details
    from expected_tables t
),
expected_policies(table_name, command_name) as (
    values
        ('sowia_documents', 'SELECT'),
        ('sowia_documents', 'INSERT'),
        ('sowia_documents', 'UPDATE'),
        ('sowia_documents', 'DELETE'),
        ('sowia_comparison_history', 'SELECT'),
        ('sowia_comparison_history', 'INSERT'),
        ('sowia_comparison_history', 'DELETE')
),
policy_checks as (
    select
        'Politique ' || p.command_name || ' sur ' || p.table_name as check_name,
        case when exists (
            select 1
            from pg_policies pol
            where pol.schemaname = 'public'
              and pol.tablename = p.table_name
              and upper(pol.cmd) = p.command_name
              and (
                  case when p.command_name in ('INSERT', 'ALL')
                      then coalesce(pol.with_check, '') ilike '%auth.uid%'
                       and coalesce(pol.with_check, '') ilike '%user_id%'
                  when p.command_name = 'UPDATE'
                      then coalesce(pol.qual, '') ilike '%auth.uid%'
                       and coalesce(pol.qual, '') ilike '%user_id%'
                       and coalesce(pol.with_check, '') ilike '%auth.uid%'
                       and coalesce(pol.with_check, '') ilike '%user_id%'
                  else coalesce(pol.qual, '') ilike '%auth.uid%'
                   and coalesce(pol.qual, '') ilike '%user_id%'
                  end
              )
        ) then 'OK' else 'À CORRIGER' end as status,
        'Une politique doit limiter cette opération à auth.uid() = user_id.' as details
    from expected_policies p
)
select check_name, status, details from table_checks
union all
select check_name, status, details from column_checks
union all
select check_name, status, details from rls_checks
union all
select check_name, status, details from policy_checks
order by check_name;
