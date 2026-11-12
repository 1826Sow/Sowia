-- Manual, rollback-only test for 20261112000100_sowia_night_exchange_secure_offers.sql.
-- Run only in SOW IA TEST after applying the migration.
-- Uses the two existing synthetic auth users A and B. No real payments.
begin;

insert into public.sowia_entitlements
    (user_id, status, provider, paypal_order_id, amount, currency, plan)
values
    ('f1792829-ca68-4815-b173-79bd13ce0ed3',
     'active', 'paypal', 'SOWIA_NEX_OFFER_TEST_A', 1, 'EUR', 'premium'),
    ('54b7271b-bc5f-4218-bad9-2b53aaa6e90f',
     'active', 'paypal', 'SOWIA_NEX_OFFER_TEST_B', 1, 'EUR', 'premium')
on conflict (user_id) do update set
    status = excluded.status,
    provider = excluded.provider,
    paypal_order_id = excluded.paypal_order_id,
    amount = excluded.amount,
    currency = excluded.currency,
    plan = excluded.plan;

create temp table sowia_nex_test_apps (
    owner_label text primary key,
    app_id uuid not null
);
create temp table sowia_nex_test_offer (
    offer_id uuid not null
);
create temp table sowia_nex_test_results (
    test text,
    outcome text
);

grant select, insert on sowia_nex_test_apps to authenticated;
grant select, insert on sowia_nex_test_offer to authenticated;
grant select, insert on sowia_nex_test_results to authenticated;

set local role authenticated;

-- Create a pending listing for each synthetic user.
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}',
    true
);
insert into public.sowia_night_exchange_apps
    (user_id, workspace_id, app_name, country, timezone, categories,
     services_offered, services_wanted)
values
    (auth.uid(), 'professional', 'NEX OFFER TEST A', 'France',
     'Europe/Paris', array['test'], 'Service A', 'Service B')
returning id;

-- Capture A's application ID.
insert into pg_temp.sowia_nex_test_apps
select 'A', id
from public.sowia_night_exchange_apps
where app_name = 'NEX OFFER TEST A'
  and user_id = auth.uid();

select set_config(
    'request.jwt.claims',
    '{"sub":"54b7271b-bc5f-4218-bad9-2b53aaa6e90f","role":"authenticated","app_metadata":{}}',
    true
);
insert into public.sowia_night_exchange_apps
    (user_id, workspace_id, app_name, country, timezone, categories,
     services_offered, services_wanted)
values
    (auth.uid(), 'professional', 'NEX OFFER TEST B', 'France',
     'Europe/Paris', array['test'], 'Service B', 'Service A');

insert into pg_temp.sowia_nex_test_apps
select 'B', id
from public.sowia_night_exchange_apps
where app_name = 'NEX OFFER TEST B'
  and user_id = auth.uid();

-- Approve both test listings using the signed admin claim.
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{"role":"admin"}}',
    true
);
select public.sowia_admin_review_nex_app(
    (select app_id from pg_temp.sowia_nex_test_apps where owner_label = 'A'),
    'approved',
    'Validation de test'
);
select public.sowia_admin_review_nex_app(
    (select app_id from pg_temp.sowia_nex_test_apps where owner_label = 'B'),
    'approved',
    'Validation de test'
);

-- A creates a proposal to B.
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}',
    true
);
insert into pg_temp.sowia_nex_test_offer
select public.sowia_nex_create_offer(
    (select app_id from pg_temp.sowia_nex_test_apps where owner_label = 'A'),
    (select app_id from pg_temp.sowia_nex_test_apps where owner_label = 'B'),
    'Proposition de test : échange de services numériques.'
);

insert into pg_temp.sowia_nex_test_results
values ('A crée une proposition', 'RÉUSSI');

-- A must not be able to answer its own outgoing offer.
do $$
begin
    begin
        perform public.sowia_nex_respond_offer(
            (select offer_id from pg_temp.sowia_nex_test_offer), 'accepted'
        );
        insert into pg_temp.sowia_nex_test_results
        values ('A tente de répondre à sa propre proposition', 'ÉCHEC : autorisé');
    exception when insufficient_privilege then
        insert into pg_temp.sowia_nex_test_results
        values ('A tente de répondre à sa propre proposition', 'BLOQUÉ');
    end;
end $$;

-- B accepts. A second response must be rejected.
select set_config(
    'request.jwt.claims',
    '{"sub":"54b7271b-bc5f-4218-bad9-2b53aaa6e90f","role":"authenticated","app_metadata":{}}',
    true
);
select public.sowia_nex_respond_offer(
    (select offer_id from pg_temp.sowia_nex_test_offer), 'accepted'
);
insert into pg_temp.sowia_nex_test_results
values ('B accepte la proposition', 'RÉUSSI');

do $$
begin
    begin
        perform public.sowia_nex_respond_offer(
            (select offer_id from pg_temp.sowia_nex_test_offer), 'accepted'
        );
        insert into pg_temp.sowia_nex_test_results
        values ('Deuxième réponse sur la même offre', 'ÉCHEC : autorisée');
    exception when sqlstate '55000' then
        insert into pg_temp.sowia_nex_test_results
        values ('Deuxième réponse sur la même offre', 'BLOQUÉE');
    end;
end $$;

-- A normal user cannot directly forge an offer_accepted ledger event.
do $$
begin
    begin
        insert into public.sowia_night_exchange_events
            (user_id, workspace_id, event_type, event_payload)
        values (
            auth.uid(), 'professional', 'offer_accepted',
            '{"test":"direct_client_forgery"}'::jsonb
        );
        insert into pg_temp.sowia_nex_test_results
        values ('Insertion client directe offer_accepted', 'ÉCHEC : autorisée');
    exception when insufficient_privilege then
        insert into pg_temp.sowia_nex_test_results
        values ('Insertion client directe offer_accepted', 'BLOQUÉE par RLS');
    end;
end $$;

-- A normal member must not be able to approve an integration.
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}',
    true
);
do $$
begin
    begin
        perform public.sowia_admin_review_nex_integration(
            (select offer_id from pg_temp.sowia_nex_test_offer),
            'approved',
            'Tentative non autorisée'
        );
        insert into pg_temp.sowia_nex_test_results
        values ('Approbation par un membre ordinaire', 'ÉCHEC : autorisée');
    exception when insufficient_privilege then
        insert into pg_temp.sowia_nex_test_results
        values ('Approbation par un membre ordinaire', 'BLOQUÉE');
    end;
end $$;

-- Only the signed administrator can approve integration.
select set_config(
    'request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{"role":"admin"}}',
    true
);
select public.sowia_admin_review_nex_integration(
    (select offer_id from pg_temp.sowia_nex_test_offer),
    'approved',
    'Validation de test'
);
insert into pg_temp.sowia_nex_test_results
values ('Approbation administrative de l’intégration', 'RÉUSSI');

-- Switch back to the migration owner so the test can inspect both participants' private audit rows.
reset role;

-- Confirm the final workflow state and both participants' audit events.
do $$
declare
    v_offer_id uuid;
    v_status text;
    v_integration_status text;
    v_events integer;
begin
    select offer_id into v_offer_id from pg_temp.sowia_nex_test_offer;

    select status, integration_status
      into v_status, v_integration_status
      from public.sowia_night_exchange_offers
     where id = v_offer_id;

    insert into pg_temp.sowia_nex_test_results
    values (
        'État final de la proposition',
        case when v_status = 'accepted'
                   and v_integration_status = 'approved'
             then 'RÉUSSI : accepted / approved'
             else 'ÉCHEC : ' || coalesce(v_status, 'NULL')
                  || ' / ' || coalesce(v_integration_status, 'NULL')
        end
    );

    select count(*) into v_events
      from public.sowia_night_exchange_events
     where event_payload ->> 'offer_id' = v_offer_id::text
       and event_type in ('offer_accepted', 'integration_approved');

    insert into pg_temp.sowia_nex_test_results
    values (
        'Journal bilatéral',
        case when v_events = 4
             then 'RÉUSSI : 4 événements pour les deux participants'
             else 'ÉCHEC : ' || v_events::text || ' événements visibles dans ce contexte'
        end
    );
end $$;

select * from pg_temp.sowia_nex_test_results order by test;

rollback;
