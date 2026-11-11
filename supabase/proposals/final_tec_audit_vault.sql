-- PROPOSAL ONLY — do not apply automatically.
-- FINAL TEC audit vault, isolated from SOWIA business/financial tables.
-- Requires Supabase's pgcrypto extension to be available in the extensions schema.

create schema if not exists final_tec_private;
revoke all on schema final_tec_private from public, anon, authenticated;
grant usage on schema final_tec_private to service_role;

create extension if not exists pgcrypto with schema extensions;

-- Allocate sequence numbers only after taking the chain lock. An IDENTITY value
-- is allocated before a BEFORE INSERT trigger runs, which can invert sequence
-- order when concurrent transactions acquire the advisory lock in another order.
create sequence if not exists final_tec_private.audit_events_sequence_id_seq;

create table if not exists final_tec_private.audit_events (
    sequence_id bigint primary key,
    event_id uuid not null unique default gen_random_uuid(),
    project_key text not null default 'final-tec'
        check (project_key = 'final-tec'),
    actor_id uuid not null,
    actor_role text not null check (
        actor_role in (
            'final_tec_admin',
            'final_tec_analyst',
            'final_tec_investor_viewer',
            'system'
        )
    ),
    action text not null check (
        action in (
            'evidence_submitted',
            'evidence_reviewed',
            'evidence_changes_requested',
            'evidence_rejected',
            'evidence_publication_requested',
            'evidence_published',
            'evidence_unpublished',
            'access_granted',
            'access_revoked',
            'investor_dashboard_viewed'
        )
    ),
    resource_type text not null check (length(resource_type) between 1 and 160),
    resource_id text not null check (length(resource_id) between 1 and 160),
    outcome text not null check (
        outcome in ('allowed', 'accepted', 'denied', 'pending', 'completed', 'failed')
    ),
    reason_code text not null check (length(reason_code) between 1 and 160),
    occurred_at timestamptz not null default clock_timestamp(),
    previous_hash text not null,
    event_hash text not null unique,
    constraint audit_hash_format check (
        previous_hash ~ '^[0-9a-f]{64}$'
        and event_hash ~ '^[0-9a-f]{64}$'
    )
);

alter table final_tec_private.audit_events enable row level security;
alter table final_tec_private.audit_events force row level security;

-- No client-facing policies are created. Access is server-only.
revoke all on final_tec_private.audit_events from public, anon, authenticated;
revoke update, delete, truncate, references, trigger
    on final_tec_private.audit_events from service_role;
grant select, insert on final_tec_private.audit_events to service_role;
grant usage, select on sequence final_tec_private.audit_events_sequence_id_seq
    to service_role;

create or replace function final_tec_private.set_audit_chain_fields()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, final_tec_private, extensions
as $$
declare
    prior_hash text;
    canonical_payload text;
begin
    -- Serialize append operations so concurrent inserts cannot fork the chain.
    perform pg_advisory_xact_lock(184631, 202611);

    -- Assign the durable ordering key while holding the same transaction lock.
    new.sequence_id := nextval('final_tec_private.audit_events_sequence_id_seq'::regclass);

    select event_hash
      into prior_hash
      from final_tec_private.audit_events
     order by sequence_id desc
     limit 1;

    new.project_key := 'final-tec';
    new.occurred_at := clock_timestamp();
    new.previous_hash := coalesce(prior_hash, repeat('0', 64));

    canonical_payload := jsonb_build_object(
        'sequence_id', new.sequence_id,
        'event_id', new.event_id,
        'project_key', new.project_key,
        'actor_id', new.actor_id,
        'actor_role', new.actor_role,
        'action', new.action,
        'resource_type', new.resource_type,
        'resource_id', new.resource_id,
        'outcome', new.outcome,
        'reason_code', new.reason_code,
        'occurred_at', new.occurred_at,
        'previous_hash', new.previous_hash
    )::text;

    new.event_hash := encode(
        extensions.digest(convert_to(canonical_payload, 'UTF8'), 'sha256'),
        'hex'
    );
    return new;
end;
$$;

create or replace function final_tec_private.reject_audit_mutation()
returns trigger
language plpgsql
set search_path = pg_catalog
as $$
begin
    raise exception 'FINAL TEC audit events are append-only';
end;
$$;

drop trigger if exists audit_events_chain_before_insert
    on final_tec_private.audit_events;
create trigger audit_events_chain_before_insert
before insert on final_tec_private.audit_events
for each row execute function final_tec_private.set_audit_chain_fields();

drop trigger if exists audit_events_no_update_delete
    on final_tec_private.audit_events;
create trigger audit_events_no_update_delete
before update or delete on final_tec_private.audit_events
for each row execute function final_tec_private.reject_audit_mutation();

drop trigger if exists audit_events_no_truncate
    on final_tec_private.audit_events;
create trigger audit_events_no_truncate
before truncate on final_tec_private.audit_events
for each statement execute function final_tec_private.reject_audit_mutation();

revoke all on function final_tec_private.set_audit_chain_fields() from public, anon, authenticated;
revoke all on function final_tec_private.reject_audit_mutation() from public, anon, authenticated;

-- IMPORTANT:
-- 1. This proposal is not a migration and has not been executed.
-- 2. service_role bypasses RLS; keep its key exclusively in trusted server secrets.
-- 3. A server endpoint must authenticate the caller and verify active FINAL TEC
--    role assignment before inserting. Never expose service_role to browser clients.
-- 4. Add independent backup/retention, restore drills, chain verification and alerting.
-- 5. Test denied anon/authenticated reads and writes with two distinct accounts.
-- 6. Review extension schema, function ownership, grants and trigger behavior in a
--    disposable Supabase project before any production approval.


create or replace function public.final_tec_append_audit_event(
    p_actor_id uuid, p_actor_role text, p_action text,
    p_resource_type text, p_resource_id text, p_outcome text, p_reason_code text
)
returns table (sequence_id bigint, event_id uuid, occurred_at timestamptz, event_hash text)
language plpgsql security definer
set search_path = pg_catalog, auth, final_tec_private
as $function$
declare
    allowed_assignment boolean;
    inserted final_tec_private.audit_events%rowtype;
begin
    if coalesce(auth.role(), '') <> 'service_role' then
        raise exception 'service_role_required';
    end if;
    if p_actor_id is null
       or p_actor_role not in ('final_tec_admin', 'final_tec_analyst', 'final_tec_investor_viewer')
       or p_action not in ('evidence_submitted','evidence_reviewed','evidence_changes_requested',
           'evidence_rejected','evidence_publication_requested','evidence_published',
           'evidence_unpublished','access_granted','access_revoked','investor_dashboard_viewed')
       or p_outcome not in ('allowed','accepted','denied','pending','completed','failed')
       or p_resource_type is null or length(trim(p_resource_type)) not between 1 and 160
       or p_resource_id is null or length(trim(p_resource_id)) not between 1 and 160
       or p_reason_code is null or p_reason_code !~ '^[a-z0-9_.-]{3,80}$' then
        raise exception 'invalid_audit_event';
    end if;
    select exists (
        select 1 from public.final_tec_investor_access a
        where a.user_id=p_actor_id and a.project_key='final-tec'
          and a.role=p_actor_role and a.status='active' and a.starts_at<=now()
          and (a.expires_at is null or a.expires_at>now())
    ) into allowed_assignment;
    if not allowed_assignment then raise exception 'active_final_tec_assignment_required'; end if;
    if (p_actor_role='final_tec_investor_viewer' and p_action<>'investor_dashboard_viewed')
       or (p_actor_role='final_tec_analyst' and p_action not in
          ('evidence_submitted','evidence_reviewed','evidence_changes_requested','evidence_rejected'))
       or (p_actor_role='final_tec_admin' and p_action='investor_dashboard_viewed') then
        raise exception 'action_not_permitted_for_role';
    end if;
    insert into final_tec_private.audit_events (
        actor_id,actor_role,action,resource_type,resource_id,outcome,reason_code,previous_hash,event_hash
    ) values (
        p_actor_id,p_actor_role,p_action,p_resource_type,p_resource_id,p_outcome,p_reason_code,
        repeat('0',64),repeat('0',64)
    ) returning * into inserted;
    return query select inserted.sequence_id,inserted.event_id,inserted.occurred_at,inserted.event_hash;
end;
$function$;

revoke all on function public.final_tec_append_audit_event(uuid,text,text,text,text,text,text)
    from public, anon, authenticated;
grant execute on function public.final_tec_append_audit_event(uuid,text,text,text,text,text,text)
    to service_role;
