-- SOW IA: READ-ONLY inventory of legacy PDF objects in the private bucket.
-- Run in the Supabase SQL Editor with an administrative account.
-- This script only reads storage.objects. It does NOT copy, move, update, or delete files.
--
-- Legacy layout:     <user_id>/<filename.pdf>
-- Personal layout:   <user_id>/personal/<filename.pdf>
-- Professional:      <user_id>/professional/<filename.pdf>
--
-- Review the counts first. The detail query intentionally returns the owner UUID
-- and object path; keep its output private and never share it publicly.

-- 1) Aggregate inventory (no user identifiers returned).
with pdf_objects as (
    select
        name,
        cardinality(storage.foldername(name)) as folder_count,
        lower(name) like '%.pdf' as is_pdf
    from storage.objects
    where bucket_id = 'sowia-files'
)
select
    count(*) filter (where is_pdf and folder_count = 1) as legacy_root_pdf_count,
    count(*) filter (
        where is_pdf and folder_count = 2
          and split_part(name, '/', 2) = 'personal'
    ) as personal_pdf_count,
    count(*) filter (
        where is_pdf and folder_count = 2
          and split_part(name, '/', 2) = 'professional'
    ) as professional_pdf_count,
    count(*) filter (where not is_pdf) as non_pdf_object_count,
    count(*) filter (
        where is_pdf and folder_count not in (1, 2)
    ) as pdf_with_unexpected_path_count
from pdf_objects;

-- 2) Legacy file details for migration planning (sensitive: owner UUID + path).
-- No file contents are read and no storage operation is performed.
select
    split_part(name, '/', 1) as owner_user_id,
    name as legacy_object_path,
    case
        when (metadata ->> 'size') ~ '^[0-9]+
    created_at
from storage.objects
where bucket_id = 'sowia-files'
  and cardinality(storage.foldername(name)) = 1
  and lower(name) like '%.pdf'
order by owner_user_id, legacy_object_path;

            then (metadata ->> 'size')::bigint
        else null
    end as size_bytes,
    created_at
from storage.objects
where bucket_id = 'sowia-files'
  and cardinality(storage.foldername(name)) = 1
  and lower(name) like '%.pdf'
order by owner_user_id, legacy_object_path;
