-- Manual rollback-only regression test for 20261113000100.
-- Run only in SOW IA TEST after applying the additive migration.
-- Synthetic users A/B must already have Premium TEST access. No entitlements/payments are changed.
begin;

create temp table nex_reject_test_apps (
    owner_label text primary key,
    app_id uuid not null
);
create temp table nex_reject_test_offer (offer_id uuid not null);
create temp table nex_reject_test_results (test text, outcome text);

grant select, insert on nex_reject_test_apps to authenticated;
grant select, insert on nex_reject_test_offer to authenticated;
grant select, insert on nex_reject_test_results to authenticated;

set local role authenticated;

select set_config('request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}', true);
insert into public.sowia_night_exchange_apps
    (user_id, workspace_id, app_name, country, timezone, categories, services_offered, services_wanted)
values (auth.uid(), 'professional', 'NEX ADMIN REJECT TEST A', 'France',
    'Europe/Paris', array['test'], 'Service A', 'Service B');
insert into pg_temp.nex_reject_test_apps
select 'A', id from public.sowia_night_exchange_apps
where app_name = 'NEX ADMIN REJECT TEST A' and user_id = auth.uid();

select set_config('request.jwt.claims',
    '{"sub":"54b7271b-bc5f-4218-bad9-2b53aaa6e90f","role":"authenticated","app_metadata":{}}', true);
insert into public.sowia_night_exchange_apps
    (user_id, workspace_id, app_name, country, timezone, categories, services_offered, services_wanted)
values (auth.uid(), 'professional', 'NEX ADMIN REJECT TEST B', 'France',
    'Europe/Paris', array['test'], 'Service B', 'Service A');
insert into pg_temp.nex_reject_test_apps
select 'B', id from public.sowia_night_exchange_apps
where app_name = 'NEX ADMIN REJECT TEST B' and user_id = auth.uid();

-- Admin A approves both synthetic app listings.
select set_config('request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{"role":"admin"}}', true);
select public.sowia_admin_review_nex_app(
    (select app_id from pg_temp.nex_reject_test_apps where owner_label = 'A'),
    'approved', 'Validation technique de test');
select public.sowia_admin_review_nex_app(
    (select app_id from pg_temp.nex_reject_test_apps where owner_label = 'B'),
    'approved', 'Validation technique de test');

-- A creates the offer.
select set_config('request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}', true);
insert into pg_temp.nex_reject_test_offer
select public.sowia_nex_create_offer(
    (select app_id from pg_temp.nex_reject_test_apps where owner_label = 'A'),
    (select app_id from pg_temp.nex_reject_test_apps where owner_label = 'B'),
    'Proposition de test : échange de services numériques.');
insert into pg_temp.nex_reject_test_results values ('Création de la proposition', 'RÉUSSI');

-- B accepts; this should create exactly two offer_accepted events.
select set_config('request.jwt.claims',
    '{"sub":"54b7271b-bc5f-4218-bad9-2b53aaa6e90f","role":"authenticated","app_metadata":{}}', true);
select public.sowia_nex_respond_offer(
    (select offer_id from pg_temp.nex_reject_test_offer), 'accepted');
insert into pg_temp.nex_reject_test_results values ('Acceptation bilatérale par B', 'RÉUSSI');

-- An ordinary member cannot reject the integration.
select set_config('request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{}}', true);
do $$
begin
    begin
        perform public.sowia_admin_review_nex_integration(
            (select offer_id from pg_temp.nex_reject_test_offer),
            'rejected', 'Tentative non autorisée');
        insert into pg_temp.nex_reject_test_results
        values ('Refus par un membre ordinaire', 'ÉCHEC : autorisé');
    exception when insufficient_privilege then
        insert into pg_temp.nex_reject_test_results
        values ('Refus par un membre ordinaire', 'BLOQUÉ');
    end;
end $$;

-- Signed administrator A rejects the integration.
select set_config('request.jwt.claims',
    '{"sub":"f1792829-ca68-4815-b173-79bd13ce0ed3","role":"authenticated","app_metadata":{"role":"admin"}}', true);
select public.sowia_admin_review_nex_integration(
    (select offer_id from pg_temp.nex_reject_test_offer),
    'rejected', 'Refus administratif de test');
insert into pg_temp.nex_reject_test_results values ('Refus par l’administrateur', 'RÉUSSI');

-- A second administrative decision must be blocked.
do $$
begin
    begin
        perform public.sowia_admin_review_nex_integration(
            (select offer_id from pg_temp.nex_reject_test_offer),
            'approved', 'Deuxième décision interdite');
        insert into pg_temp.nex_reject_test_results
        values ('Deuxième décision administrative', 'ÉCHEC : autorisée');
    exception when sqlstate '55000' then
        insert into pg_temp.nex_reject_test_results
        values ('Deuxième décision administrative', 'BLOQUÉE');
    end;
end $$;

reset role;

-- Verify final state, bilateral audit rows, and moderation metadata.
do $$
declare
    v_offer_id uuid;
    v_status text;
    v_integration_status text;
    v_note text;
    v_reviewed_at timestamptz;
    v_reviewed_by uuid;
    v_accept_count integer;
    v_reject_count integer;
    v_approve_count integer;
    v_bad_reject_count integer;
begin
    select offer_id into v_offer_id from pg_temp.nex_reject_test_offer;
    select status, integration_status, integration_review_note,
           integration_reviewed_at, integration_reviewed_by
      into v_status, v_integration_status, v_note, v_reviewed_at, v_reviewed_by
      from public.sowia_night_exchange_offers where id = v_offer_id;

    insert into pg_temp.nex_reject_test_results values (
        'État final de la proposition',
        case when v_status = 'accepted' and v_integration_status = 'rejected'
             then 'RÉUSSI : accepted / rejected'
             else 'ÉCHEC : ' || coalesce(v_status, 'NULL') || ' / ' || coalesce(v_integration_status, 'NULL') end);

    insert into pg_temp.nex_reject_test_results values (
        'Note et identité de modération',
        case when v_note = 'Refus administratif de test'
                   and v_reviewed_at is not null
                   and v_reviewed_by = 'f1792829-ca68-4815-b173-79bd13ce0ed3'::uuid
             then 'RÉUSSI : note, date et administrateur enregistrés'
             else 'ÉCHEC : métadonnées de modération incohérentes' end);

    select count(*) into v_accept_count from public.sowia_night_exchange_events
     where event_payload ->> 'offer_id' = v_offer_id::text and event_type = 'offer_accepted';
    select count(*) into v_reject_count from public.sowia_night_exchange_events
     where event_payload ->> 'offer_id' = v_offer_id::text and event_type = 'integration_rejected';
    select count(*) into v_approve_count from public.sowia_night_exchange_events
     where event_payload ->> 'offer_id' = v_offer_id::text and event_type = 'integration_approved';
    select count(*) into v_bad_reject_count from public.sowia_night_exchange_events
     where event_payload ->> 'offer_id' = v_offer_id::text
       and event_type = 'integration_rejected'
       and (event_payload ->> 'rejected_by' <> 'f1792829-ca68-4815-b173-79bd13ce0ed3'
            or event_payload ->> 'review_note' <> 'Refus administratif de test');

    insert into pg_temp.nex_reject_test_results values (
        'Journal des acceptations bilatérales',
        case when v_accept_count = 2 then 'RÉUSSI : 2 événements attendus'
             else 'ÉCHEC : ' || v_accept_count::text || ' événement(s)' end);
    insert into pg_temp.nex_reject_test_results values (
        'Journal bilatéral integration_rejected',
        case when v_reject_count = 2 and v_bad_reject_count = 0
             then 'RÉUSSI : 2 événements, administrateur et note vérifiés'
             else 'ÉCHEC : ' || v_reject_count::text || ' événement(s), métadonnées invalides : ' || v_bad_reject_count::text end);
    insert into pg_temp.nex_reject_test_results values (
        'Absence de fausse approbation',
        case when v_approve_count = 0 then 'RÉUSSI : aucun événement integration_approved'
             else 'ÉCHEC : ' || v_approve_count::text || ' événement(s)' end);
end $$;

select * from pg_temp.nex_reject_test_results order by test;
rollback;
