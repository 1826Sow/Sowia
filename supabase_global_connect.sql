-- SOWIA GLOBAL CONNECT: consent-based professional connection requests.
-- Apply AFTER supabase_global_id.sql and supabase_global_directory.sql.
begin;

create table if not exists public.sowia_global_connection_requests (
    id uuid primary key default gen_random_uuid(),
    requester_id uuid not null references auth.users(id) on delete cascade,
    recipient_id uuid not null references auth.users(id) on delete cascade,
    requester_profile_id uuid not null references public.sowia_global_profiles(id) on delete cascade,
    recipient_profile_id uuid not null references public.sowia_global_profiles(id) on delete cascade,
    message text not null,
    status text not null default 'pending'
        check (status in ('pending','accepted','declined','cancelled')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint sowia_global_connect_not_self check (requester_id <> recipient_id),
    constraint sowia_global_connect_message_length check (
        pg_catalog.char_length(pg_catalog.btrim(message)) between 10 and 1000
    )
);

create unique index if not exists sowia_global_connect_one_pending_pair
    on public.sowia_global_connection_requests(requester_id, recipient_id)
    where status = 'pending';
create index if not exists sowia_global_connect_inbox_idx
    on public.sowia_global_connection_requests(recipient_id, created_at desc);
create index if not exists sowia_global_connect_outbox_idx
    on public.sowia_global_connection_requests(requester_id, created_at desc);

alter table public.sowia_global_connection_requests enable row level security;
revoke all on public.sowia_global_connection_requests from anon, public;
grant select on public.sowia_global_connection_requests to authenticated;
grant insert, update on public.sowia_global_connection_requests to authenticated;

drop policy if exists sowia_global_connect_select_participant on public.sowia_global_connection_requests;
create policy sowia_global_connect_select_participant
on public.sowia_global_connection_requests for select to authenticated
using (auth.uid() = requester_id or auth.uid() = recipient_id);

drop policy if exists sowia_global_connect_insert_requester on public.sowia_global_connection_requests;
create policy sowia_global_connect_insert_requester
on public.sowia_global_connection_requests for insert to authenticated
with check (
    auth.uid() = requester_id
    and requester_id <> recipient_id
    and status = 'pending'
    and exists (
        select 1 from public.sowia_global_profiles sender
        where sender.id = requester_profile_id
          and sender.user_id = auth.uid()
          and sender.is_published = true
          and sender.verification_status <> 'suspended'
    )
    and exists (
        select 1 from public.sowia_global_profiles target
        where target.id = recipient_profile_id
          and target.user_id = recipient_id
          and target.is_published = true
          and target.verification_status <> 'suspended'
    )
);

-- No direct client update is allowed; state transitions go through the RPCs below.
drop policy if exists sowia_global_connect_no_direct_update on public.sowia_global_connection_requests;
create policy sowia_global_connect_no_direct_update
on public.sowia_global_connection_requests for update to authenticated
using (false) with check (false);

create or replace function public.sowia_global_connect_request(p_public_id text, p_message text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_sender_profile uuid;
    v_recipient_profile uuid;
    v_recipient uuid;
    v_request uuid;
    v_message text := pg_catalog.btrim(coalesce(p_message, ''));
begin
    if auth.uid() is null then
        raise exception 'Authentication required';
    end if;
    if pg_catalog.char_length(v_message) < 10 or pg_catalog.char_length(v_message) > 1000 then
        raise exception 'Message must contain 10 to 1000 characters';
    end if;

    select id into v_sender_profile
    from public.sowia_global_profiles
    where user_id = auth.uid() and is_published = true
      and verification_status <> 'suspended'
    limit 1;
    if v_sender_profile is null then
        raise exception 'Publish your own GLOBAL ID profile before contacting partners';
    end if;

    select id, user_id into v_recipient_profile, v_recipient
    from public.sowia_global_profiles
    where public_id = p_public_id and is_published = true
      and verification_status <> 'suspended'
    limit 1;
    if v_recipient_profile is null or v_recipient = auth.uid() then
        raise exception 'Target profile is unavailable';
    end if;

    insert into public.sowia_global_connection_requests
        (requester_id, recipient_id, requester_profile_id, recipient_profile_id, message)
    values (auth.uid(), v_recipient, v_sender_profile, v_recipient_profile, v_message)
    returning id into v_request;
    return v_request;
end;
$$;

create or replace function public.sowia_global_connect_respond(p_request_id uuid, p_decision text)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_rows integer;
begin
    if auth.uid() is null then raise exception 'Authentication required'; end if;
    if p_decision not in ('accepted','declined') then
        raise exception 'Invalid decision';
    end if;
    update public.sowia_global_connection_requests
       set status = p_decision, updated_at = now()
     where id = p_request_id and recipient_id = auth.uid() and status = 'pending';
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

create or replace function public.sowia_global_connect_cancel(p_request_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_rows integer;
begin
    if auth.uid() is null then raise exception 'Authentication required'; end if;
    update public.sowia_global_connection_requests
       set status = 'cancelled', updated_at = now()
     where id = p_request_id and requester_id = auth.uid() and status = 'pending';
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

revoke all on function public.sowia_global_connect_request(text,text) from public, anon;
revoke all on function public.sowia_global_connect_respond(uuid,text) from public, anon;
revoke all on function public.sowia_global_connect_cancel(uuid) from public, anon;
grant execute on function public.sowia_global_connect_request(text,text) to authenticated;
grant execute on function public.sowia_global_connect_respond(uuid,text) to authenticated;
grant execute on function public.sowia_global_connect_cancel(uuid) to authenticated;

comment on table public.sowia_global_connection_requests is
'Private consent-based professional connection requests. Only the two participants can read a request. Contact details are never revealed automatically.';

commit;
