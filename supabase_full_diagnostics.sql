-- SOW IA: READ-ONLY deployment diagnostic.
-- Inventory based on the SQL migrations and persistence modules currently in the repository.
-- Run only after the corresponding feature migrations have been applied in Supabase.
-- This script reads PostgreSQL catalog and Storage metadata only; it changes no data or schema.

with expected_tables(table_name, is_optional) as (
    values
        ('sowia_messages', false),
        ('sowia_memory_items', false),
        ('sowia_entitlements', false),
        ('sowia_subscriptions', true),
        ('sowia_paypal_catalog', true),
        ('sowia_financial_transactions', true),
        ('sowia_technical_incidents', true),
        ('sowia_growth_leads', false),
        ('sowia_user_preferences', false),
        ('sowia_relationship_events', true),
        ('sowia_business_opportunities', false),
        ('sowia_business_club_profiles', true),
        ('sowia_business_club_requests', true),
        ('sowia_business_club_meetings', true),
        ('sowia_business_club_notifications', true),
        ('sowia_vip_printer_suppliers', true),
        ('sowia_vip_printer_quotes', true),
        ('sowia_vip_printer_reviews', true),
        ('sowia_vip_card_orders', true),
        ('sowia_night_exchange_apps', true),
        ('sowia_night_exchange_events', true),
        ('sowia_global_profiles', true),
        ('sowia_global_connection_requests', true),
        ('sowia_global_messages', true),
        ('sowia_global_notifications', true),
        ('sowia_global_notification_preferences', true),
        ('sowia_global_trust_reviews', true),
        ('sowia_global_trust_reports', true),
        ('sowia_global_moderation_audit', true),
        ('sowia_global_intelligence_assessments', true),
        ('sowia_global_pulse_items', true),
        ('sowia_global_alerts', true),
        ('sowia_global_forecasts', true),
        ('sowia_global_decisions', true),
        ('sowia_global_learning_records', true),
        ('sowia_global_action_plans', true),
        ('sowia_global_action_audit', true),
        ('sowia_global_performance_observations', true),
        ('sowia_global_projects', true),
        ('sowia_global_project_members', true),
        ('sowia_global_project_contributions', true),
        ('sowia_global_project_milestones', true),
        ('sowia_global_project_audit', true),
        ('sowia_decision_trials', true),
        ('sowia_crypto_orders', true),
        ('sowia_crypto_payment_events', true),
        ('sowia_technology_candidates', true)
),
table_checks as (
    select
        'table'::text as check_type,
        e.table_name::text as object_name,
        case
            when c.oid is null and e.is_optional then 'OPTIONAL - NOT INSTALLED'
            when c.oid is null then 'MISSING'
            when c.relkind not in ('r', 'p') then 'WRONG OBJECT TYPE'
            else 'PRESENT'
        end as status,
        case
            when c.oid is null then 'Required table public.' || e.table_name || ' not found'
            when c.relkind not in ('r', 'p') then 'Found object is not a regular or partitioned table'
            else 'RLS enabled=' || c.relrowsecurity::text
                 || '; RLS forced=' || c.relforcerowsecurity::text
        end as detail
    from expected_tables e
    left join pg_namespace n on n.nspname = 'public'
    left join pg_class c on c.relnamespace = n.oid and c.relname = e.table_name
),
rls_checks as (
    select
        'RLS status'::text as check_type,
        e.table_name::text as object_name,
        case
            when c.oid is null and e.is_optional then 'OPTIONAL - NOT INSTALLED'
            when c.oid is null then 'MISSING'
            when c.relkind not in ('r', 'p') then 'NOT A TABLE'
            when c.relrowsecurity then 'ENABLED'
            else 'DISABLED - REVIEW'
        end as status,
        case
            when c.oid is null and e.is_optional then 'Optional feature table is not installed; no RLS check applies yet'
            when c.oid is null then 'Cannot inspect RLS because the required table is absent'
            when c.relkind not in ('r', 'p') then 'RLS check applies to tables only'
            when c.relrowsecurity then 'Row Level Security is enabled'
            else 'Private application data may be exposed unless access is otherwise blocked'
        end as detail
    from expected_tables e
    left join pg_namespace n on n.nspname = 'public'
    left join pg_class c on c.relnamespace = n.oid and c.relname = e.table_name
),
expected_views(view_name) as (
    values
        ('sowia_global_profiles_public'),
        ('sowia_global_trust_public')
),
view_checks as (
    select
        'view'::text as check_type,
        e.view_name::text as object_name,
        case when c.oid is null then 'OPTIONAL - NOT INSTALLED' when c.relkind in ('v','m') then 'PRESENT' else 'WRONG OBJECT TYPE' end as status,
        case when c.oid is null then 'Optional public view is not installed'
             else 'View relkind=' || c.relkind::text end as detail
    from expected_views e
    left join pg_namespace n on n.nspname = 'public'
    left join pg_class c on c.relnamespace = n.oid and c.relname = e.view_name
),
expected_columns(table_name, column_name, is_optional) as (
    values
        ('sowia_messages', 'user_id', false),
        ('sowia_messages', 'session_id', false),
        ('sowia_messages', 'role', false),
        ('sowia_messages', 'content', false),
        ('sowia_messages', 'workspace_id', false),
        ('sowia_memory_items', 'user_id', false),
        ('sowia_memory_items', 'content', false),
        ('sowia_memory_items', 'workspace_id', false),
        ('sowia_entitlements', 'user_id', false),
        ('sowia_entitlements', 'status', false),
        ('sowia_entitlements', 'provider', true),
        ('sowia_entitlements', 'paypal_order_id', true),
        ('sowia_growth_leads', 'user_id', false),
        ('sowia_growth_leads', 'workspace_id', false),
        ('sowia_growth_leads', 'organization', false),
        ('sowia_growth_leads', 'country', false),
        ('sowia_growth_leads', 'status', false),
        ('sowia_growth_leads', 'source_url', false),
        ('sowia_user_preferences', 'user_id', false),
        ('sowia_user_preferences', 'language', false),
        ('sowia_user_preferences', 'updated_at', false),
        ('sowia_business_opportunities', 'user_id', false),
        ('sowia_business_opportunities', 'workspace_id', false),
        ('sowia_business_opportunities', 'niche', false),
        ('sowia_business_opportunities', 'offer', false),
        ('sowia_business_opportunities', 'stage', false),
        ('sowia_business_opportunities', 'expected_monthly_revenue', false),
        ('sowia_business_opportunities', 'estimated_monthly_cost', false),
        ('sowia_business_opportunities', 'currency', false),
        ('sowia_financial_transactions', 'user_id', true),
        ('sowia_financial_transactions', 'provider', true),
        ('sowia_financial_transactions', 'status', true),
        ('sowia_night_exchange_apps', 'user_id', true),
        ('sowia_night_exchange_apps', 'workspace_id', true),
        ('sowia_global_profiles', 'user_id', true),
        ('sowia_global_profiles', 'is_published', true),
        ('sowia_global_connection_requests', 'requester_id', true),
        ('sowia_global_connection_requests', 'recipient_id', true),
        ('sowia_global_messages', 'sender_id', true),
        ('sowia_global_messages', 'recipient_id', true),
        ('sowia_vip_card_orders', 'user_id', true),
        ('sowia_vip_card_orders', 'status', true)
),
column_checks as (
    select
        'column'::text as check_type,
        (e.table_name || '.' || e.column_name)::text as object_name,
        case when c.column_name is null and e.is_optional then 'OPTIONAL - NOT INSTALLED'
             when c.column_name is null then 'MISSING' else 'PRESENT' end as status,
        case when c.column_name is null and e.is_optional then 'Optional feature column is not installed'
             else coalesce(c.data_type, 'Expected column is absent from public schema')::text end as detail
    from expected_columns e
    left join information_schema.columns c
        on c.table_schema = 'public'
       and c.table_name = e.table_name
       and c.column_name = e.column_name
),
expected_buckets(bucket_id) as (
    values ('sowia-files')
),
bucket_checks as (
    select
        'storage bucket'::text as check_type,
        e.bucket_id::text as object_name,
        case when b.id is null then 'MISSING'
             when b.public then 'PUBLIC - REVIEW'
             else 'PRIVATE' end as status,
        case when b.id is null then 'Expected private bucket not found'
             else 'file_size_limit=' || coalesce(b.file_size_limit::text, '<null>')
                  || '; allowed_mime_types=' || coalesce(b.allowed_mime_types::text, '<null>')
        end as detail
    from expected_buckets e
    left join storage.buckets b on b.id = e.bucket_id
)
select check_type, object_name, status, detail from table_checks
union all
select check_type, object_name, status, detail from rls_checks
union all
select check_type, object_name, status, detail from view_checks
union all
select check_type, object_name, status, detail from column_checks
union all
select check_type, object_name, status, detail from bucket_checks
union all
select
    'table policy'::text,
    schemaname || '.' || tablename || ' / ' || policyname,
    cmd::text,
    'roles=' || coalesce(roles::text, '<null>')
        || '; USING=' || coalesce(qual, '<none>')
        || '; WITH CHECK=' || coalesce(with_check, '<none>')
from pg_policies
where schemaname = 'public'
  and tablename in (select table_name from expected_tables)
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
