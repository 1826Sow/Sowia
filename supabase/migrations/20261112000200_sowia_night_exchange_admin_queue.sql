-- SOWIA NIGHT EXCHANGE: administrator-only integration review queue.
-- Additive migration. No payment processing or payment records.
begin;

create or replace function public.sowia_admin_list_nex_integrations()
returns table (
    id uuid,
    sender_user_id uuid,
    recipient_user_id uuid,
    sender_app_id uuid,
    recipient_app_id uuid,
    offer_summary text,
    status text,
    integration_status text,
    integration_review_note text,
    created_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
begin
    if auth.uid() is null or not (
        coalesce(auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce(auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    ) then
        raise exception 'Accès administrateur requis' using errcode = '42501';
    end if;

    return query
    select o.id, o.sender_user_id, o.recipient_user_id,
           o.sender_app_id, o.recipient_app_id, o.offer_summary,
           o.status, o.integration_status, o.integration_review_note,
           o.created_at
      from public.sowia_night_exchange_offers o
     where o.status = 'accepted'
       and o.integration_status = 'pending'
       and o.workspace_id = 'professional'
     order by o.created_at asc
     limit 200;
end;
$$;

revoke all on function public.sowia_admin_list_nex_integrations() from public, anon;
grant execute on function public.sowia_admin_list_nex_integrations() to authenticated;

comment on function public.sowia_admin_list_nex_integrations() is
'Returns only accepted NIGHT EXCHANGE offers awaiting integration review, and only to a signed SOWIA administrator.';

commit;
