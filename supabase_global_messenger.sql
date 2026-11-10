begin;

create table if not exists public.sowia_global_messages (
    id uuid primary key default gen_random_uuid(),
    request_id uuid not null references public.sowia_global_connection_requests(id) on delete cascade,
    sender_id uuid not null references auth.users(id) on delete cascade,
    recipient_id uuid not null references auth.users(id) on delete cascade,
    body text not null check (char_length(body) between 1 and 4000),
    created_at timestamptz not null default now(),
    constraint sowia_global_messages_distinct_participants check (sender_id <> recipient_id)
);

create index if not exists sowia_global_messages_conversation_idx
    on public.sowia_global_messages(request_id, created_at, id);

alter table public.sowia_global_messages enable row level security;
drop policy if exists sowia_global_messages_participant_read on public.sowia_global_messages;
create policy sowia_global_messages_participant_read
    on public.sowia_global_messages for select to authenticated
    using (
        exists (
            select 1 from public.sowia_global_connection_requests r
            where r.id = request_id
              and auth.uid() in (r.requester_id, r.recipient_id)
        )
    );

revoke all on public.sowia_global_messages from anon, authenticated;
grant select on public.sowia_global_messages to authenticated;

create or replace function public.sowia_global_send_message(p_request_id uuid, p_message text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_uid uuid := auth.uid();
    v_recipient uuid;
    v_status text;
    v_message text := pg_catalog.btrim(coalesce(p_message, ''));
    v_id uuid;
    v_recent integer;
begin
    if v_uid is null then raise exception 'Authentication required'; end if;
    if pg_catalog.char_length(v_message) < 1 or pg_catalog.char_length(v_message) > 4000 then
        raise exception 'Message must contain 1 to 4000 characters';
    end if;

    select
        case when requester_id = v_uid then recipient_id else requester_id end,
        status
      into v_recipient, v_status
      from public.sowia_global_connection_requests
     where id = p_request_id
       and v_uid in (requester_id, recipient_id)
     for update;

    if v_recipient is null or v_status <> 'accepted' then
        raise exception 'An accepted connection is required';
    end if;

    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(v_uid::text, 0)
    );
    select count(*) into v_recent
      from public.sowia_global_messages
     where sender_id = v_uid
       and created_at > now() - interval '1 minute';
    if v_recent >= 20 then raise exception 'Message rate limit reached'; end if;

    insert into public.sowia_global_messages(request_id, sender_id, recipient_id, body)
    values (p_request_id, v_uid, v_recipient, v_message)
    returning id into v_id;
    return v_id;
end;
$$;

revoke all on function public.sowia_global_send_message(uuid,text) from public, anon;
grant execute on function public.sowia_global_send_message(uuid,text) to authenticated;

comment on table public.sowia_global_messages is
'Private append-only messages between participants in an accepted SOWIA GLOBAL CONNECT request.';

commit;
