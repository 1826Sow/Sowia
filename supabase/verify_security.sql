-- SOW IA — read-only Supabase security verification
-- Run ONLY after applying supabase/schema.sql in the disposable test project.
-- This script does not modify tables, policies, grants, users, or storage objects.
-- It inspects configuration only; it does NOT replace the two-account end-to-end tests.

-- 1) Confirm that RLS is enabled on the application tables.
select
    n.nspname as schema_name,
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements')
order by c.relname;

-- 2) Inspect row-level security policies for application tables and private files.
select
    schemaname,
    tablename,
    policyname,
    roles,
    cmd,
    qual,
    with_check
from pg_policies
where (schemaname = 'public'
       and tablename in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements'))
   or (schemaname = 'storage' and tablename = 'objects')
order by schemaname, tablename, policyname;

-- 3) Inspect client table grants. Expected:
-- messages/memory: authenticated SELECT, INSERT, DELETE only.
-- entitlements: authenticated SELECT only.
-- anon: no grants on these private application tables.
select
    grantee,
    table_schema,
    table_name,
    privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements')
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, privilege_type;

-- 4) Confirm the private PDF bucket configuration.
select
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
from storage.buckets
where id = 'sowia-private-documents';

-- Expected bucket: public=false, file_size_limit=10485760,
-- allowed_mime_types includes application/pdf.
