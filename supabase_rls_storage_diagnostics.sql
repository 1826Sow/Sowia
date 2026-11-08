-- SOW IA: READ-ONLY diagnostic for table RLS and private PDF Storage.
-- Run in Supabase SQL Editor using a role allowed to inspect catalog metadata.
-- This script only reads metadata. It does not change tables, policies, grants, buckets, or files.

-- 1) Row Level Security status for SOW IA application tables.
select
    n.nspname as schema_name,
    c.relname as table_name,
    c.relrowsecurity as rls_enabled,
    c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind in ('r', 'p')
  and n.nspname = 'public'
  and c.relname in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements')
order by c.relname;

-- 2) Policies installed on those application tables.
select
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual as using_expression,
    with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('sowia_messages', 'sowia_memory_items', 'sowia_entitlements')
order by tablename, policyname;

-- 3) Private PDF bucket configuration.
select
    id as bucket_id,
    public as is_public,
    file_size_limit,
    allowed_mime_types
from storage.buckets
where id = 'sowia-files';

-- 4) Every policy on storage.objects, including policies outside SOW IA.
-- Review unexpected permissive policies: permissive policies are OR-combined.
select
    policyname,
    permissive,
    roles,
    cmd,
    qual as using_expression,
    with_check
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
order by policyname;
