-- SOW IA: read-only post-migration security verification.
-- Run in Supabase SQL Editor AFTER applying the documented migrations.
-- This script only reads PostgreSQL catalog metadata; it changes no data or schema.

with expected_columns(table_name, column_name) as (
    values
        ('sowia_documents', 'user_id'),
        ('sowia_documents', 'title'),
        ('sowia_documents', 'filename'),
        ('sowia_documents', 'extracted_text'),
        ('sowia_documents', 'text_length'),
        ('sowia_documents', 'created_at'),
        ('sowia_documents', 'category'),
        ('sowia_documents', 'folder'),
        ('sowia_documents', 'deleted_at'),
        ('sowia_comparison_history', 'user_id'),
        ('sowia_comparison_history', 'report'),
        ('sowia_comparison_history', 'created_at'),
        ('sowia_memory_items', 'user_id'),
        ('sowia_memory_items', 'content'),
        ('sowia_memory_items', 'created_at'),
        ('sowia_messages', 'user_id'),
        ('sowia_messages', 'session_id'),
        ('sowia_messages', 'role'),
        ('sowia_messages', 'content'),
        ('sowia_messages', 'created_at')
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
    values
        ('sowia_documents'),
        ('sowia_comparison_history'),
        ('sowia_memory_items'),
        ('sowia_messages')
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
        ('sowia_comparison_history', 'DELETE'),
        ('sowia_memory_items', 'SELECT'),
        ('sowia_memory_items', 'INSERT'),
        ('sowia_memory_items', 'DELETE'),
        ('sowia_messages', 'SELECT'),
        ('sowia_messages', 'INSERT'),
        ('sowia_messages', 'DELETE')
),
document_constraint_checks as (
    select
        'Contrainte de taille du texte extrait' as check_name,
        case when exists (
            select 1
            from pg_constraint c
            where c.conrelid = to_regclass('public.sowia_documents')
              and c.contype = 'c'
              and pg_get_constraintdef(c.oid) ilike '%char_length(extracted_text)%'
              and pg_get_constraintdef(c.oid) ilike '%100000%'
        ) then 'OK' else 'À CORRIGER' end as status,
        'Le texte extrait doit rester limité à 100 000 caractères.' as details
    union all
    select
        'Contrainte de catégorie des documents',
        case when exists (
            select 1
            from pg_constraint c
            where c.conrelid = to_regclass('public.sowia_documents')
              and c.contype = 'c'
              and pg_get_constraintdef(c.oid) ilike '%category%'
              and pg_get_constraintdef(c.oid) ilike '%Finances%'
              and pg_get_constraintdef(c.oid) ilike '%Autres%'
        ) then 'OK' else 'À CORRIGER' end,
        'La catégorie doit respecter la liste autorisée.'
    union all
    select
        'Contrainte de longueur du dossier',
        case when exists (
            select 1
            from pg_constraint c
            where c.conrelid = to_regclass('public.sowia_documents')
              and c.contype = 'c'
              and pg_get_constraintdef(c.oid) ilike '%folder%'
              and pg_get_constraintdef(c.oid) ilike '%60%'
        ) then 'OK' else 'À CORRIGER' end,
        'Le nom du dossier doit être limité à 60 caractères.'
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
              and 'authenticated'::name = any(pol.roles)
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
union all
select check_name, status, details from document_constraint_checks
union all
select
    'Index de corbeille sowia_documents_user_deleted_idx' as check_name,
    case when exists (
        select 1 from pg_indexes
        where schemaname = 'public'
          and tablename = 'sowia_documents'
          and indexname = 'sowia_documents_user_deleted_idx'
          and indexdef ilike '%(user_id, deleted_at, created_at%'
    ) then 'OK' else 'À CORRIGER' end as status,
    'L’index utilisateur/corbeille/date doit exister pour les recherches de corbeille.' as details
order by check_name;
