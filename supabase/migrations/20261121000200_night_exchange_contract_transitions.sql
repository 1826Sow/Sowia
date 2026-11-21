-- NIGHT EXCHANGE controlled contract transitions.
-- Additive proposal only: do not apply to production without isolated PostgreSQL/RLS tests.
-- This RPC changes contract status and appends its audit event in one transaction.
-- Payment, refund and commission events remain outside this client-callable function.

alter table public.sowia_nex_deal_events
    add column if not exists idempotency_key text;

create unique index if not exists sowia_nex_deal_events_actor_idempotency_uidx
    on public.sowia_nex_deal_events (actor_user_id, idempotency_key)
    where idempotency_key is not null;

create or replace function public.sowia_nex_transition_deal(
    p_deal_id uuid,
    p_target_status text,
    p_idempotency_key text,
    p_note text default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor uuid := auth.uid();
    v_deal public.sowia_nex_deals%rowtype;
    v_existing_event_id uuid;
    v_existing_deal_id uuid;
    v_event_id uuid;
    v_previous_status text;
begin
    if v_actor is null then
        raise exception 'authentication required' using errcode = '42501';
    end if;

    if p_deal_id is null
       or p_target_status not in ('accepted', 'in_progress', 'completed', 'cancelled', 'disputed')
       or p_idempotency_key is null
       or char_length(p_idempotency_key) < 16
       or char_length(p_idempotency_key) > 128
       or (p_note is not null and char_length(p_note) > 1000) then
        raise exception 'invalid transition request' using errcode = '22023';
    end if;

    select *
      into v_deal
      from public.sowia_nex_deals
     where id = p_deal_id
     for update;

    if not found then
        raise exception 'deal not found' using errcode = 'P0002';
    end if;

    if v_actor <> v_deal.created_by
       and v_actor is distinct from v_deal.counterparty_user_id then
        raise exception 'not a deal participant' using errcode = '42501';
    end if;

    -- A retry with the same key returns the original event and never repeats a transition.
    select id, deal_id
      into v_existing_event_id, v_existing_deal_id
      from public.sowia_nex_deal_events
     where actor_user_id = v_actor
       and idempotency_key = p_idempotency_key;

    if found then
        if v_existing_deal_id <> p_deal_id then
            raise exception 'idempotency key already used for another deal'
                using errcode = '23505';
        end if;
        return v_existing_event_id;
    end if;

    v_previous_status := v_deal.status;

    if v_previous_status = 'proposed'
       and p_target_status = 'accepted'
       and v_actor = v_deal.counterparty_user_id then
        null;
    elsif v_previous_status = 'proposed'
       and p_target_status = 'cancelled'
       and v_actor = v_deal.created_by then
        null;
    elsif v_previous_status = 'accepted'
       and p_target_status in ('in_progress', 'cancelled') then
        null;
    elsif v_previous_status = 'in_progress'
       and p_target_status = 'completed'
       and v_actor = v_deal.counterparty_user_id then
        null;
    elsif v_previous_status in ('proposed', 'accepted', 'in_progress')
       and p_target_status = 'disputed' then
        null;
    else
        raise exception 'transition not permitted: % -> %',
            v_previous_status, p_target_status
            using errcode = '23514';
    end if;

    update public.sowia_nex_deals
       set status = p_target_status,
           updated_at = now()
     where id = p_deal_id;

    insert into public.sowia_nex_deal_events (
        deal_id,
        actor_user_id,
        event_type,
        event_payload,
        idempotency_key
    )
    values (
        p_deal_id,
        v_actor,
        'status_changed',
        jsonb_build_object(
            'from', v_previous_status,
            'to', p_target_status,
            'note', p_note
        ),
        p_idempotency_key
    )
    returning id into v_event_id;

    return v_event_id;
end;
$$;

-- No anonymous/public execution. The function itself verifies auth.uid() and participation.
revoke all on function public.sowia_nex_transition_deal(uuid, text, text, text)
    from public, anon, authenticated;
grant execute on function public.sowia_nex_transition_deal(uuid, text, text, text)
    to authenticated;

comment on function public.sowia_nex_transition_deal(uuid, text, text, text) is
    'Atomically validates a participant contract transition and appends an immutable status_changed event. Does not confirm payment, refund or commission.';
