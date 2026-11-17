-- Secure, read-only discovery of legacy message sessions for the signed-in user.
-- RLS on sowia_messages remains in force (security invoker).
create or replace function public.sowia_list_legacy_conversations(p_workspace_id text)
returns table (
    session_id text,
    first_user_message text,
    first_message_at timestamptz,
    message_count bigint
)
language sql
stable
security invoker
set search_path = public
as $$
    select
        m.session_id,
        (array_agg(m.content order by m.id) filter (where m.role = 'user'))[1] as first_user_message,
        min(m.created_at) as first_message_at,
        count(*) as message_count
    from public.sowia_messages as m
    where m.user_id = (select auth.uid())
      and m.workspace_id = p_workspace_id
      and p_workspace_id in ('personal', 'professional')
    group by m.session_id
    order by max(m.id) desc
    limit 100;
$$;

revoke all on function public.sowia_list_legacy_conversations(text) from public, anon;
grant execute on function public.sowia_list_legacy_conversations(text) to authenticated;
