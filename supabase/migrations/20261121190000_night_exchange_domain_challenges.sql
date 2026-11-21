-- NIGHT EXCHANGE domain-proof persistence.
-- Draft migration: do not apply to production until reviewed and the server resolver is ready.
-- The raw TXT token is never stored; the trusted server passes SHA-256(token) as 32 bytes.

create schema if not exists sowia_private;
revoke all on schema sowia_private from public, anon, authenticated;
grant usage on schema sowia_private to service_role;

create table if not exists sowia_private.nex_domain_challenges (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    domain text not null
        check (
            domain = lower(domain)
            and char_length(domain) between 4 and 253
            and domain ~ '^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$'
        ),
    token_hash bytea not null check (octet_length(token_hash) = 32),
    issued_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    consumed_at timestamptz,
    check (expires_at > issued_at),
    check (consumed_at is null or consumed_at >= issued_at)
);

create index if not exists nex_domain_challenges_owner_domain_expiry_idx
    on sowia_private.nex_domain_challenges (owner_id, domain, expires_at desc);

create table if not exists sowia_private.nex_domain_verification_audit (
    id bigint generated always as identity primary key,
    challenge_id uuid not null,
    owner_id uuid not null,
    domain text not null,
    event_type text not null
        check (event_type in ('challenge_issued', 'proof_consumed')),
    occurred_at timestamptz not null default clock_timestamp()
);

create index if not exists nex_domain_verification_audit_owner_time_idx
    on sowia_private.nex_domain_verification_audit (owner_id, occurred_at desc);

alter table sowia_private.nex_domain_challenges enable row level security;
alter table sowia_private.nex_domain_verification_audit enable row level security;

revoke all on table sowia_private.nex_domain_challenges
    from public, anon, authenticated, service_role;
revoke all on table sowia_private.nex_domain_verification_audit
    from public, anon, authenticated, service_role;

create or replace function sowia_private.issue_nex_domain_challenge(
    p_owner_id uuid,
    p_domain text,
    p_token_hash bytea,
    p_ttl_seconds integer default 86400
)
returns table (challenge_id uuid, expires_at timestamptz, dns_host text)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_id uuid := gen_random_uuid();
    v_issued_at timestamptz := clock_timestamp();
    v_expires_at timestamptz;
    v_domain text := lower(btrim(p_domain));
begin
    if p_owner_id is null then
        raise exception 'Authenticated owner required' using errcode = '22023';
    end if;
    if v_domain is null
       or char_length(v_domain) not between 4 and 253
       or v_domain !~ '^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$' then
        raise exception 'Invalid normalized domain' using errcode = '22023';
    end if;
    if p_token_hash is null or octet_length(p_token_hash) <> 32 then
        raise exception 'A SHA-256 token digest is required' using errcode = '22023';
    end if;
    if p_ttl_seconds is null or p_ttl_seconds < 300 or p_ttl_seconds > 172800 then
        raise exception 'Challenge TTL must be between 300 and 172800 seconds' using errcode = '22023';
    end if;

    v_expires_at := v_issued_at + pg_catalog.make_interval(secs => p_ttl_seconds);

    insert into sowia_private.nex_domain_challenges
        (id, owner_id, domain, token_hash, issued_at, expires_at)
    values
        (v_id, p_owner_id, v_domain, p_token_hash, v_issued_at, v_expires_at);

    insert into sowia_private.nex_domain_verification_audit
        (challenge_id, owner_id, domain, event_type, occurred_at)
    values
        (v_id, p_owner_id, v_domain, 'challenge_issued', v_issued_at);

    return query
    select v_id, v_expires_at, '_sowia-verification.' || v_domain;
end;
$$;

create or replace function sowia_private.consume_nex_domain_challenge(
    p_challenge_id uuid,
    p_owner_id uuid,
    p_domain text,
    p_token_hash bytea
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_owner_id uuid;
    v_domain text;
    v_consumed_at timestamptz := clock_timestamp();
begin
    if p_challenge_id is null or p_owner_id is null
       or p_domain is null or p_token_hash is null
       or octet_length(p_token_hash) <> 32 then
        return false;
    end if;

    -- A single conditional UPDATE is the atomic one-time-use gate.
    -- Concurrent replays serialize on the row; exactly one call can consume it.
    update sowia_private.nex_domain_challenges as c
       set consumed_at = v_consumed_at
     where c.id = p_challenge_id
       and c.owner_id = p_owner_id
       and c.domain = lower(btrim(p_domain))
       and c.token_hash = p_token_hash
       and c.consumed_at is null
       and c.expires_at > v_consumed_at
    returning c.owner_id, c.domain into v_owner_id, v_domain;

    if not found then
        return false;
    end if;

    insert into sowia_private.nex_domain_verification_audit
        (challenge_id, owner_id, domain, event_type, occurred_at)
    values
        (p_challenge_id, v_owner_id, v_domain, 'proof_consumed', v_consumed_at);

    return true;
end;
$$;

revoke all on function sowia_private.issue_nex_domain_challenge(uuid, text, bytea, integer)
    from public, anon, authenticated;
revoke all on function sowia_private.consume_nex_domain_challenge(uuid, uuid, text, bytea)
    from public, anon, authenticated;
grant execute on function sowia_private.issue_nex_domain_challenge(uuid, text, bytea, integer)
    to service_role;
grant execute on function sowia_private.consume_nex_domain_challenge(uuid, uuid, text, bytea)
    to service_role;

comment on schema sowia_private is
    'Non-exposed SOW IA server-only data and functions. Never expose service_role credentials to clients.';
comment on table sowia_private.nex_domain_challenges is
    'Single-use NIGHT EXCHANGE DNS challenges. Stores only SHA-256 token digests; no client role has table access.';
comment on table sowia_private.nex_domain_verification_audit is
    'Append-only audit events for NIGHT EXCHANGE domain challenge issuance and successful consumption.';
