-- SOWIA — contrôle préalable du registre financier et du journal d'audit
-- SCRIPT STRICTEMENT LECTURE SEULE : aucun CREATE, ALTER, INSERT, UPDATE ou DELETE.
-- À exécuter dans Supabase > SQL Editor uniquement pour afficher les prérequis.
-- Ne révèle aucune ligne de paiement, aucun identifiant client ni aucun secret.

with expected_columns(table_name, column_name, expected_type) as (
    values
      ('sowia_financial_transactions', 'id', 'uuid'),
      ('sowia_financial_transactions', 'user_id', 'uuid'),
      ('sowia_financial_transactions', 'order_id', 'uuid'),
      ('sowia_financial_transactions', 'reference_amount_eur', 'numeric'),
      ('sowia_financial_transactions', 'tax_amount_eur', 'numeric'),
      ('sowia_financial_transactions', 'created_at', 'timestamp with time zone'),
      ('sowia_financial_transactions', 'provider', 'text'),
      ('sowia_financial_transactions', 'provider_payment_id', 'text'),
      ('sowia_financial_transactions', 'parent_capture_id', 'text'),
      ('sowia_financial_transactions', 'transaction_type', 'text'),
      ('sowia_financial_transactions', 'status', 'text'),
      ('sowia_financial_transactions', 'gross_amount', 'numeric'),
      ('sowia_financial_transactions', 'gross_currency', 'text'),
      ('sowia_financial_transactions', 'fee_amount', 'numeric'),
      ('sowia_financial_transactions', 'fee_currency', 'text'),
      ('sowia_financial_transactions', 'net_amount', 'numeric'),
      ('sowia_financial_transactions', 'net_currency', 'text'),
      ('sowia_financial_transactions', 'occurred_at', 'timestamp with time zone')
),
column_checks as (
    select
      e.table_name,
      e.column_name,
      e.expected_type,
      c.data_type as actual_type,
      case
        when c.column_name is null then 'ABSENT'
        when c.data_type = e.expected_type then 'OK'
        else 'TYPE_MISMATCH'
      end as result
    from expected_columns e
    left join information_schema.columns c
      on c.table_schema = 'public'
     and c.table_name = e.table_name
     and c.column_name = e.column_name
),
table_checks as (
    select
      'sowia_financial_transactions'::text as table_name,
      'table_exists'::text as column_name,
      'present'::text as expected_type,
      case when to_regclass('public.sowia_financial_transactions') is null
           then 'absent' else 'present' end as actual_type,
      case when to_regclass('public.sowia_financial_transactions') is null
           then 'ABSENT' else 'OK' end as result
    union all
    select
      'sowia_financial_transactions',
      'row_level_security',
      'enabled',
      coalesce(c.relrowsecurity::text, 'table_absent'),
      case when c.relrowsecurity is true then 'OK'
           when c.oid is null then 'TABLE_ABSENT'
           else 'RLS_DISABLED' end
    from (select oid, relrowsecurity
          from pg_class
          where oid = to_regclass('public.sowia_financial_transactions')) c
),
audit_checks as (
    select
      'sowia_financial_audit_log'::text as table_name,
      'audit_table'::text as column_name,
      'present after audit migration'::text as expected_type,
      case when to_regclass('public.sowia_financial_audit_log') is null
           then 'absent' else 'present' end as actual_type,
      case when to_regclass('public.sowia_financial_audit_log') is null
           then 'NOT_YET_APPLIED' else 'PRESENT' end as result
    union all
    select
      'sowia_financial_transactions',
      'audit_trigger',
      'present after audit migration',
      case when exists (
        select 1 from pg_trigger
        where tgrelid = to_regclass('public.sowia_financial_transactions')
          and tgname = 'sowia_financial_ledger_audit'
          and not tgisinternal
      ) then 'present' else 'absent' end,
      case when exists (
        select 1 from pg_trigger
        where tgrelid = to_regclass('public.sowia_financial_transactions')
          and tgname = 'sowia_financial_ledger_audit'
          and not tgisinternal
      ) then 'PRESENT' else 'NOT_YET_APPLIED' end
)
select table_name, column_name, expected_type, actual_type, result
from column_checks
union all
select table_name, column_name, expected_type, actual_type, result
from table_checks
union all
select table_name, column_name, expected_type, actual_type, result
from audit_checks
order by table_name, column_name;
