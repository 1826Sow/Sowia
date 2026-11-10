-- SOW IA: READ-ONLY deployment diagnostic.
-- Inventory based on the SQL migrations and persistence modules currently in the repository.
-- Run only after the corresponding feature migrations have been applied in Supabase.
-- This script reads PostgreSQL catalog and Storage metadata only; it changes no data or schema.

with expected_tables(table_name) as (
    values
        ('sowia_messages'),
        ('sowia_memory_items'),
        ('sowia_entitlements'),
        ('sowia_subscriptions'),
        ('sowia_paypal_catalog'),
        ('sowia_financial_transactions'),
        ('sowia_technical_incidents'),
        ('sowia_growth_leads'),
        ('sowia_user_preferences'),
        ('sowia_relationship_events'),
        ('sowia_business_opportunities'),
        ('sowia_business_club_profiles'),
        ('sowia_business_club_requests'),
        ('sowia_business_club_meetings'),
        ('sowia_business_club_notifications'),
        ('sowia_vip_printer_suppliers'),
        ('sowia_vip_printer_quotes'),
        ('sowia_vip_printer_reviews'),
        ('sowia_vip_card_orders'),
        ('sowia_night_exchange_apps'),
        ('sowia_night_exchange_events'),
        ('sowia_global_profiles'),
        ('sowia_global_connection_requests'),
        ('sowia_global_messages'),
        ('sowia_global_notifications'),
        ('sowia_global_notification_preferences'),
        ('sowia_global_trust_reviews'),
        ('sowia_global_trust_reports'),
        ('sowia_global_moderation_audit'),
        ('sowia_global_intelligence_assessments'),
        ('sowia_global_pulse_items'),
        ('sowia_global_alerts'),
        ('sowia_global_forecasts'),
        ('sowia_global_decisions'),
        ('sowia_global_learning_records'),
        ('sowia_global_action_plans'),
        ('sowia_global_action_audit'),
        ('sowia_global_performance_observations'),
        ('sowia_global_projects'),
        ('sowia_global_project_members'),
        ('sowia_global_project_contributions'),
        ('sowia_global_project_milestones'),
        ('sowia_global_project_audit'),
        ('sowia_decision_trials'),
        ('sowia_crypto_orders'),
        ('sowia_crypto_payment_events'),
        ('sowia_technology_candidates')
),
table_checks as (
    select
        'table'::text as check_type,
        e.table_name::text as object_name,
        case
            when c.oid is null then 'MISSING'
            when c.relkind not in ('r', 'p') then 'WRONG OBJECT TYPE'
            else 'PRESENT'
        end as status,
        case
            when c.oid is null then 'Table public.' || e.table_name || ' not found'
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
            when c.oid is null then 'MISSING'
            when c.relkind not in ('r', 'p') then 'NOT A TABLE'
            when c.relrowsecurity then 'ENABLED'
            else 'DISABLED - REVIEW'
        end as status,
        case
            when c.oid is null then 'Cannot inspect RLS because the table is absent'
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
        case when c.oid is null then 'MISSING' when c.relkind in ('v','m') then 'PRESENT' else 'WRONG OBJECT TYPE' end as status,
        case when c.oid is null then 'Expected public view not found'
             else 'View relkind=' || c.relkind::text end as detail
    from expected_views e
    left join pg_namespace n on n.nspname = 'public'
    left join pg_class c on c.relnamespace = n.oid and c.relname = e.view_name
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
        ('sowia_user_preferences', 'updated_at'),
        ('sowia_business_opportunities', 'user_id'),
        ('sowia_business_opportunities', 'workspace_id'),
        ('sowia_business_opportunities', 'niche'),
        ('sowia_business_opportunities', 'offer'),
        ('sowia_business_opportunities', 'stage'),
        ('sowia_business_opportunities', 'expected_monthly_revenue'),
        ('sowia_business_opportunities', 'estimated_monthly_cost'),
        ('sowia_business_opportunities', 'currency'),
        ('sowia_financial_transactions', 'user_id'),
        ('sowia_financial_transactions', 'provider'),
        ('sowia_financial_transactions', 'status'),
        ('sowia_night_exchange_apps', 'user_id'),
        ('sowia_night_exchange_apps', 'workspace_id'),
        ('sowia_global_profiles', 'user_id'),
        ('sowia_global_profiles', 'is_published'),
        ('sowia_global_connection_requests', 'requester_id'),
        ('sowia_global_connection_requests', 'recipient_id'),
        ('sowia_global_messages', 'sender_id'),
        ('sowia_global_messages', 'recipient_id'),
        ('sowia_vip_card_orders', 'user_id'),
        ('sowia_vip_card_orders', 'status')
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
