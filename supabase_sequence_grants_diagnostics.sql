-- SOW IA: READ-ONLY diagnostic for effective sequence privileges.
-- Run in Supabase SQL Editor before changing sequence grants.
-- This reports the privileges actually available to the authenticated role.
-- It does not grant, revoke, alter, or delete anything.

select
    n.nspname as schema_name,
    c.relname as sequence_name,
    has_sequence_privilege('authenticated', c.oid, 'USAGE') as authenticated_usage,
    has_sequence_privilege('authenticated', c.oid, 'SELECT') as authenticated_select,
    has_sequence_privilege('authenticated', c.oid, 'UPDATE') as authenticated_update,
    case
        when c.relname in ('sowia_messages_id_seq', 'sowia_memory_items_id_seq')
            then 'required by SOW IA identity inserts'
        else 'review before any privilege change'
    end as review_note
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where c.relkind = 'S'
  and n.nspname = 'public'
order by
    case when c.relname in ('sowia_messages_id_seq', 'sowia_memory_items_id_seq') then 0 else 1 end,
    c.relname;
