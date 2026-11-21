-- NIGHT EXCHANGE proposal creation audit.
-- Automatically append the proposal event when a commercial deal is created.
-- This is additive and remains unapplied to production.

create or replace function public.sowia_nex_audit_deal_proposal()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.sowia_nex_deal_events (
        deal_id,
        actor_user_id,
        event_type,
        event_payload
    )
    values (
        new.id,
        new.created_by,
        'proposal_created',
        jsonb_build_object(
            'workspace_id', new.workspace_id,
            'deal_kind', new.deal_kind,
            'title', new.title
        )
    );

    return new;
end;
$$;

revoke all on function public.sowia_nex_audit_deal_proposal()
    from public, anon, authenticated;

drop trigger if exists sowia_nex_deals_audit_proposal on public.sowia_nex_deals;
create trigger sowia_nex_deals_audit_proposal
    after insert on public.sowia_nex_deals
    for each row execute function public.sowia_nex_audit_deal_proposal();

comment on function public.sowia_nex_audit_deal_proposal() is
    'Internal trigger function: append a proposal_created event for each new NIGHT EXCHANGE deal.';
