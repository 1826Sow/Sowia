-- SOW IA: read-only Supabase security diagnostics.
-- Run ONLY as a project administrator in a dedicated TEST project before
-- enabling the live two-user RLS integration tests.
-- This script does not create, alter, or delete any object or policy.

-- 1) Show every policy on storage.objects, not just policies with known names.
-- PostgreSQL permissive policies combine with OR; an old broad policy can
-- therefore weaken a newer owner/workspace policy.
select
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
from pg_catalog.pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
order by policyname, cmd;

-- 2) Show RLS and FORCE RLS state for SOW IA tables and Storage objects.
select
    n.nspname as schema_name,
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as force_rls
from pg_catalog.pg_class c
join pg_catalog.pg_namespace n on n.oid = c.relnamespace
where (n.nspname = 'public'
       and c.relname in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements'))
   or (n.nspname = 'storage' and c.relname = 'objects')
order by n.nspname, c.relname;

-- 3) Show grants to application-facing roles on SOW IA tables and sequences.
-- Review unexpected INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER grants.
select
    table_schema,
    table_name,
    grantee,
    privilege_type,
    is_grantable
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements')
  and grantee in ('anon', 'authenticated', 'service_role', 'PUBLIC')
order by table_name, grantee, privilege_type;

select
    object_schema as sequence_schema,
    object_name as sequence_name,
    grantee,
    privilege_type,
    is_grantable
from information_schema.role_usage_grants
where object_type = 'SEQUENCE'
  and object_schema = 'public'
  and grantee in ('anon', 'authenticated', 'service_role', 'PUBLIC')
order by sequence_name, grantee, privilege_type;

-- 4) Confirm the private bucket configuration.
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
where id = 'sowia-files';

-- Interpretation:
-- * Every storage.objects policy must be reviewed, including policies whose
--   names do not start with "SOW IA".
-- * Investigate any permissive policy that grants broad access to this bucket
--   or omits owner-folder checks. Do not assume a policy is safe from its name.
-- * Require RLS enabled on all listed application tables and storage.objects.
-- * Authenticated should not have INSERT/UPDATE/DELETE on sowia_entitlements.
-- * anon should have no table privileges on SOW IA private data.
-- * sowia-files must report public = false.
-- These diagnostics are evidence for review, not an automated security
-- certification. A human must inspect the returned expressions and grants.
