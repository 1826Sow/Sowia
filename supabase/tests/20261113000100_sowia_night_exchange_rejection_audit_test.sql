-- Rollback-only regression test for bilateral integration rejection audit.
-- Run in SOWIA TEST while the synthetic offer below is accepted / pending.
begin;

select set_config(
    'request.jwt.claim.sub',
    'f1792829-ca68-4815-b173-79bd13ce0ed3',
    true
);
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{"sowia_admin":true}}',
    true
);

select public.sowia_admin_review_nex_integration(
    '41cb5363-87f7-417a-a8c8-65c9370322e9',
    'rejected',
    'TEST REFUS - ROLLBACK'
);

do $$
declare
    v_state text;
    v_events integer;
    v_participants integer;
begin
    select integration_status
      into v_state
      from public.sowia_night_exchange_offers
     where id = '41cb5363-87f7-417a-a8c8-65c9370322e9';

    select count(*), count(distinct user_id)
      into v_events, v_participants
      from public.sowia_night_exchange_events
     where event_type = 'integration_rejected'
       and event_payload ->> 'offer_id' = '41cb5363-87f7-417a-a8c8-65c9370322e9';

    if v_state <> 'rejected' then
        raise exception 'FAIL: integration_status attendu rejected, reçu %', v_state;
    end if;
    if v_events <> 2 or v_participants <> 2 then
        raise exception 'FAIL: attendu 2 événements pour 2 participants, reçu % événements / % participants',
            v_events, v_participants;
    end if;
    raise notice 'PASS: refus enregistré et journalisé pour les deux participants';
end;
$$;

rollback;
