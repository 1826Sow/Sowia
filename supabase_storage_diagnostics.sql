-- SOW IA: READ-ONLY diagnostic for the private PDF bucket and Storage policies.
-- Run AFTER supabase_storage_policies.sql in Supabase SQL Editor.
-- This script only reads catalog data; it does not create, alter, or delete anything.

select
    'bucket'::text as check_type,
    id::text as object_name,
    public::text as setting,
    concat(
        'file_size_limit=', coalesce(file_size_limit::text, '<null>'),
        '; allowed_mime_types=', coalesce(allowed_mime_types::text, '<null>')
    ) as detail
from storage.buckets
where id = 'sowia-files'

union all

select
    'storage.objects policy'::text as check_type,
    policyname::text as object_name,
    cmd::text as setting,
    concat(
        'roles=', coalesce(roles::text, '<null>'),
        '; USING=', coalesce(qual, '<none>'),
        '; WITH CHECK=', coalesce(with_check, '<none>')
    ) as detail
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'

order by check_type, object_name;
