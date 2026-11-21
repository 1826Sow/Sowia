-- NIGHT EXCHANGE persistent commercial mission register.
-- Additive only. No payment processing, settlement, or third-party execution.
begin;

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.sowia_nex_missions (
    id uuid primary key default gen_random_uuid(),
    workspace_id text not null default 'professional'
        check (workspace_id = 'professional'),
    requester_user_id uuid not null references auth.users(id) on delete restrict,
    provider_user_id uuid not null references auth.users(id) on delete restrict,
    requester_app_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    provider_app_id uuid not null references public.sowia_night_exchange_apps(id) on delete restrict,
    terms jsonb not null check (jsonb_typeof(terms) = 'object'),
    terms_hash text not null check (terms_hash ~ '^[0-9a-f]{64}$'),
    requester_approved_hash text,
    provider_approved_hash text,
    status text not null default 'proposed'
        check (status in ('proposed','accepted','in_progress','delivered','completed','cancelled','disputed')),
    delivered_at timestamptz,
    completed_at timestamptz,
    cancelled_at timestamptz,
    dispute_reason text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    check (requester_user_id <> provider_user_id),
    check (requester_app_id <> provider_app_id),
    check (requester_approved_hash is null or requester_approved_hash = terms_hash),
    check (provider_approved_hash is null or provider_approved_hash = terms_hash)
);

create index if not exists sowia_nex_missions_requester_idx
    on public.sowia_nex_missions(requester_user_id, created_at desc);
create index if not exists sowia_nex_missions_provider_idx
    on public.sowia_nex_missions(provider_user_id, created_at desc);
create index if not exists sowia_nex_missions_status_idx
    on public.sowia_nex_missions(status, updated_at desc);

create table if not exists public.sowia_nex_mission_events (
    id bigint generated always as identity primary key,
    mission_id uuid not null references public.sowia_nex_missions(id) on delete restrict,
    actor_user_id uuid not null references auth.users(id) on delete restrict,
    event_type text not null check (event_type in (
        'mission_proposed','owner_approved','mission_started',
        'deliverable_submitted','deliverable_accepted',
        'mission_cancelled','dispute_opened'
    )),
    previous_status text,
    new_status text not null,
    terms_hash text not null check (terms_hash ~ '^[0-9a-f]{64}$'),
    event_details jsonb not null default '{}'::jsonb
        check (jsonb_typeof(event_details) = 'object'
               and octet_length(event_details::text) <= 2048),
    created_at timestamptz not null default now()
);

create index if not exists sowia_nex_mission_events_mission_idx
    on public.sowia_nex_mission_events(mission_id, created_at asc);

alter table public.sowia_nex_missions enable row level security;
alter table public.sowia_nex_mission_events enable row level security;

drop policy if exists "nex_missions_participants_read" on public.sowia_nex_missions;
create policy "nex_missions_participants_read"
    on public.sowia_nex_missions for select to authenticated
    using (auth.uid() = requester_user_id or auth.uid() = provider_user_id);

drop policy if exists "nex_mission_events_participants_read" on public.sowia_nex_mission_events;
create policy "nex_mission_events_participants_read"
    on public.sowia_nex_mission_events for select to authenticated
    using (exists (
        select 1 from public.sowia_nex_missions m
        where m.id = mission_id
          and (m.requester_user_id = auth.uid() or m.provider_user_id = auth.uid())
    ));

revoke all on public.sowia_nex_missions from anon, authenticated;
revoke all on public.sowia_nex_mission_events from anon, authenticated;
grant select on public.sowia_nex_missions, public.sowia_nex_mission_events to authenticated;
grant usage, select on sequence public.sowia_nex_mission_events_id_seq to authenticated;

create or replace function public.sowia_nex_create_mission(
    p_provider_app_id uuid,
    p_requester_app_id uuid,
    p_title text,
    p_scope text,
    p_deliverable text,
    p_quoted_amount numeric,
    p_currency text,
    p_due_at timestamptz default null
)
returns uuid
language plpgsql
security definer
set search_path = pg_catalog, extensions, pg_temp
as $$
declare
    v_actor uuid := auth.uid();
    v_provider_user uuid;
    v_requester_app_owner uuid;
    v_requester_app_status text;
    v_provider_app_status text;
    v_terms jsonb;
    v_hash text;
    v_id uuid;
begin
    if v_actor is null then
        raise exception 'Authentification requise' using errcode = '42501';
    end if;
    if p_provider_app_id is null or p_requester_app_id is null
       or p_provider_app_id = p_requester_app_id then
        raise exception 'Deux applications distinctes sont requises' using errcode = '22023';
    end if;
    if p_title is null or char_length(btrim(p_title)) not between 1 and 160
       or p_scope is null or char_length(btrim(p_scope)) not between 1 and 3000
       or p_deliverable is null or char_length(btrim(p_deliverable)) not between 1 and 1000 then
        raise exception 'Titre, périmètre ou livrable invalide' using errcode = '22023';
    end if;
    if p_quoted_amount is null or p_quoted_amount <= 0 or p_quoted_amount > 999999999.99
       or p_currency is null or upper(btrim(p_currency)) !~ '^[A-Z]{3}$' then
        raise exception 'Devis positif et devise à trois lettres requis' using errcode = '22023';
    end if;

    select user_id, status into v_requester_app_owner, v_requester_app_status
      from public.sowia_night_exchange_apps
     where id = p_requester_app_id and workspace_id = 'professional';
    if not found or v_requester_app_owner <> v_actor or v_requester_app_status <> 'approved' then
        raise exception 'Application demandeuse non autorisée ou non approuvée' using errcode = '42501';
    end if;

    select user_id, status into v_provider_user, v_provider_app_status
      from public.sowia_night_exchange_apps
     where id = p_provider_app_id and workspace_id = 'professional';
    if not found or v_provider_app_status <> 'approved' or v_provider_user = v_actor then
        raise exception 'Application prestataire non approuvée ou propriétaire identique' using errcode = '42501';
    end if;

    v_terms := jsonb_build_object(
        'title', btrim(p_title),
        'scope', btrim(p_scope),
        'deliverable', btrim(p_deliverable),
        'quoted_amount', to_char(round(p_quoted_amount, 2), 'FM999999999990.00'),
        'currency', upper(btrim(p_currency)),
        'due_at', p_due_at
    );
    v_hash := encode(extensions.digest(convert_to(v_terms::text, 'UTF8'), 'sha256'), 'hex');

    insert into public.sowia_nex_missions (
        requester_user_id, provider_user_id, requester_app_id, provider_app_id,
        terms, terms_hash, status
    ) values (
        v_actor, v_provider_user, p_requester_app_id, p_provider_app_id,
        v_terms, v_hash, 'proposed'
    ) returning id into v_id;

    insert into public.sowia_nex_mission_events (
        mission_id, actor_user_id, event_type, previous_status, new_status, terms_hash
    ) values (v_id, v_actor, 'mission_proposed', null, 'proposed', v_hash);
    return v_id;
end;
$$;

create or replace function public.sowia_nex_approve_mission(p_mission_id uuid)
returns text
language plpgsql
security definer
set search_path = pg_catalog, extensions, pg_temp
as $$
declare
    v_actor uuid := auth.uid();
    v_row public.sowia_nex_missions%rowtype;
    v_hash text;
    v_status text;
begin
    if v_actor is null then
        raise exception 'Authentification requise' using errcode = '42501';
    end if;
    select * into v_row from public.sowia_nex_missions
     where id = p_mission_id for update;
    if not found or v_actor not in (v_row.requester_user_id, v_row.provider_user_id) then
        raise exception 'Mission introuvable ou accès refusé' using errcode = '42501';
    end if;
    if v_row.status <> 'proposed' then
        raise exception 'Cette proposition n''est plus ouverte à approbation' using errcode = '22023';
    end if;
    v_hash := encode(extensions.digest(convert_to(v_row.terms::text, 'UTF8'), 'sha256'), 'hex');
    if v_hash <> v_row.terms_hash then
        raise exception 'Les conditions ont changé; approbations invalidées' using errcode = '22023';
    end if;

    if v_actor = v_row.requester_user_id then
        update public.sowia_nex_missions
           set requester_approved_hash = v_hash, updated_at = now()
         where id = p_mission_id;
        insert into public.sowia_nex_mission_events
            (mission_id, actor_user_id, event_type, previous_status, new_status, terms_hash)
        values (p_mission_id, v_actor, 'owner_approved', 'proposed', 'proposed', v_hash);
    else
        update public.sowia_nex_missions
           set provider_approved_hash = v_hash, updated_at = now()
         where id = p_mission_id;
        insert into public.sowia_nex_mission_events
            (mission_id, actor_user_id, event_type, previous_status, new_status, terms_hash)
        values (p_mission_id, v_actor, 'owner_approved', 'proposed', 'proposed', v_hash);
    end if;

    select * into v_row from public.sowia_nex_missions
     where id = p_mission_id for update;
    if v_row.requester_approved_hash = v_hash and v_row.provider_approved_hash = v_hash then
        update public.sowia_nex_missions
           set status = 'accepted', updated_at = now()
         where id = p_mission_id;
        insert into public.sowia_nex_mission_events
            (mission_id, actor_user_id, event_type, previous_status, new_status, terms_hash)
        values (p_mission_id, v_actor, 'owner_approved', 'proposed', 'accepted', v_hash);
        v_status := 'accepted';
    else
        v_status := 'proposed';
    end if;
    return v_status;
end;
$$;

create or replace function public.sowia_nex_transition_mission(
    p_mission_id uuid,
    p_action text,
    p_reason text default null
)
returns text
language plpgsql
security definer
set search_path = pg_catalog, extensions, pg_temp
as $$
declare
    v_actor uuid := auth.uid();
    v_row public.sowia_nex_missions%rowtype;
    v_hash text;
    v_next text;
    v_event text;
begin
    if v_actor is null then
        raise exception 'Authentification requise' using errcode = '42501';
    end if;
    select * into v_row from public.sowia_nex_missions
     where id = p_mission_id for update;
    if not found or v_actor not in (v_row.requester_user_id, v_row.provider_user_id) then
        raise exception 'Mission introuvable ou accès refusé' using errcode = '42501';
    end if;

    v_hash := encode(extensions.digest(convert_to(v_row.terms::text, 'UTF8'), 'sha256'), 'hex');
    if v_hash <> v_row.terms_hash
       or (v_row.status <> 'proposed' and (
            v_row.requester_approved_hash is distinct from v_hash
            or v_row.provider_approved_hash is distinct from v_hash
       )) then
        raise exception 'Conditions ou approbations incohérentes; transition bloquée' using errcode = '22023';
    end if;

    if p_action = 'start' and v_actor = v_row.provider_user_id and v_row.status = 'accepted' then
        v_next := 'in_progress'; v_event := 'mission_started';
    elsif p_action = 'deliver' and v_actor = v_row.provider_user_id and v_row.status = 'in_progress' then
        v_next := 'delivered'; v_event := 'deliverable_submitted';
    elsif p_action = 'accept_delivery' and v_actor = v_row.requester_user_id and v_row.status = 'delivered' then
        v_next := 'completed'; v_event := 'deliverable_accepted';
    elsif p_action = 'cancel' and v_row.status in ('proposed','accepted') then
        v_next := 'cancelled'; v_event := 'mission_cancelled';
    elsif p_action = 'dispute' and v_row.status in ('delivered','completed')
          and p_reason is not null and char_length(btrim(p_reason)) between 1 and 1000 then
        v_next := 'disputed'; v_event := 'dispute_opened';
    else
        raise exception 'Transition non autorisée pour cet acteur ou cet état' using errcode = '42501';
    end if;

    update public.sowia_nex_missions
       set status = v_next,
           delivered_at = case when v_next = 'delivered' then now() else delivered_at end,
           completed_at = case when v_next = 'completed' then now() else completed_at end,
           cancelled_at = case when v_next = 'cancelled' then now() else cancelled_at end,
           dispute_reason = case when v_next = 'disputed' then btrim(p_reason) else dispute_reason end,
           updated_at = now()
     where id = p_mission_id;

    insert into public.sowia_nex_mission_events (
        mission_id, actor_user_id, event_type, previous_status, new_status,
        terms_hash, event_details
    ) values (
        p_mission_id, v_actor, v_event, v_row.status, v_next, v_hash,
        case when v_next = 'disputed' then jsonb_build_object('reason', btrim(p_reason))
             else '{}'::jsonb end
    );
    return v_next;
end;
$$;

revoke all on function public.sowia_nex_create_mission(uuid, uuid, text, text, text, numeric, text, timestamptz) from public, anon;
revoke all on function public.sowia_nex_approve_mission(uuid) from public, anon;
revoke all on function public.sowia_nex_transition_mission(uuid, text, text) from public, anon;
grant execute on function public.sowia_nex_create_mission(uuid, uuid, text, text, text, numeric, text, timestamptz) to authenticated;
grant execute on function public.sowia_nex_approve_mission(uuid) to authenticated;
grant execute on function public.sowia_nex_transition_mission(uuid, text, text) to authenticated;

comment on table public.sowia_nex_missions is
'Persistent bilateral NIGHT EXCHANGE mission register. No payment processing or automated execution.';
comment on table public.sowia_nex_mission_events is
'Append-only audit trail for NIGHT EXCHANGE mission lifecycle transitions.';

commit;
