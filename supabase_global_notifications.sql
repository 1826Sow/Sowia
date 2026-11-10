-- SOWIA GLOBAL NOTIFICATIONS: private in-app event notifications and language preferences.
-- Apply AFTER supabase_global_messenger.sql.
begin;

create table if not exists public.sowia_global_notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    event_type text not null check (event_type in (
        'connection_request_received','connection_request_accepted',
        'connection_request_declined','new_message'
    )),
    reference_id uuid not null,
    created_at timestamptz not null default now(),
    read_at timestamptz,
    constraint sowia_global_notifications_event_reference_unique
        unique(user_id, event_type, reference_id)
);
create index if not exists sowia_global_notifications_inbox_idx
    on public.sowia_global_notifications(user_id, created_at desc);

create table if not exists public.sowia_global_notification_preferences (
    user_id uuid primary key references auth.users(id) on delete cascade,
    language text not null default 'fr'
        check (language in ('fr','en','es','pt','zh','ar')),
    in_app_enabled boolean not null default true,
    updated_at timestamptz not null default now()
);

alter table public.sowia_global_notifications enable row level security;
alter table public.sowia_global_notification_preferences enable row level security;
revoke all on public.sowia_global_notifications from anon, public, authenticated;
revoke all on public.sowia_global_notification_preferences from anon, public, authenticated;
grant select on public.sowia_global_notifications to authenticated;
grant select on public.sowia_global_notification_preferences to authenticated;

drop policy if exists sowia_global_notifications_read_own on public.sowia_global_notifications;
create policy sowia_global_notifications_read_own
on public.sowia_global_notifications for select to authenticated
using (user_id = auth.uid());

drop policy if exists sowia_global_notification_preferences_read_own on public.sowia_global_notification_preferences;
create policy sowia_global_notification_preferences_read_own
on public.sowia_global_notification_preferences for select to authenticated
using (user_id = auth.uid());

create or replace function public.sowia_global_notification_add(
    p_user_id uuid, p_event_type text, p_reference_id uuid
) returns void
language plpgsql security definer set search_path = ''
as $$
declare v_enabled boolean;
begin
    if p_user_id is null or p_reference_id is null then return; end if;
    select coalesce(p.in_app_enabled, true) into v_enabled
      from public.sowia_global_notification_preferences p
     where p.user_id = p_user_id;
    if v_enabled is false then return; end if;
    insert into public.sowia_global_notifications(user_id,event_type,reference_id)
    values (p_user_id,p_event_type,p_reference_id)
    on conflict (user_id,event_type,reference_id) do nothing;
end;
$$;

create or replace function public.sowia_global_notify_connect_request()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    perform public.sowia_global_notification_add(
        new.recipient_id,'connection_request_received',new.id
    );
    return new;
end;
$$;

create or replace function public.sowia_global_notify_connect_response()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    if old.status = 'pending' and new.status in ('accepted','declined') then
        perform public.sowia_global_notification_add(
            new.requester_id,
            case when new.status = 'accepted'
                 then 'connection_request_accepted'
                 else 'connection_request_declined' end,
            new.id
        );
    end if;
    return new;
end;
$$;

create or replace function public.sowia_global_notify_new_message()
returns trigger language plpgsql security definer set search_path = ''
as $$
begin
    perform public.sowia_global_notification_add(
        new.recipient_id,'new_message',new.id
    );
    return new;
end;
$$;

drop trigger if exists sowia_global_notify_connect_request_trg on public.sowia_global_connection_requests;
create trigger sowia_global_notify_connect_request_trg
after insert on public.sowia_global_connection_requests
for each row execute function public.sowia_global_notify_connect_request();

drop trigger if exists sowia_global_notify_connect_response_trg on public.sowia_global_connection_requests;
create trigger sowia_global_notify_connect_response_trg
after update of status on public.sowia_global_connection_requests
for each row execute function public.sowia_global_notify_connect_response();

drop trigger if exists sowia_global_notify_new_message_trg on public.sowia_global_messages;
create trigger sowia_global_notify_new_message_trg
after insert on public.sowia_global_messages
for each row execute function public.sowia_global_notify_new_message();

create or replace function public.sowia_global_notifications_mark_read(p_notification_id uuid)
returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_rows integer;
begin
    if auth.uid() is null then raise exception 'Authentication required'; end if;
    update public.sowia_global_notifications
       set read_at = now()
     where id = p_notification_id and user_id = auth.uid() and read_at is null;
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

create or replace function public.sowia_global_notifications_mark_all_read()
returns integer language plpgsql security definer set search_path = ''
as $$
declare v_rows integer;
begin
    if auth.uid() is null then raise exception 'Authentication required'; end if;
    update public.sowia_global_notifications
       set read_at = now()
     where user_id = auth.uid() and read_at is null;
    get diagnostics v_rows = row_count;
    return v_rows;
end;
$$;

create or replace function public.sowia_global_notification_set_preferences(
    p_language text, p_in_app_enabled boolean
) returns boolean language plpgsql security definer set search_path = ''
as $$
begin
    if auth.uid() is null then raise exception 'Authentication required'; end if;
    if p_language not in ('fr','en','es','pt','zh','ar') then
        raise exception 'Unsupported notification language';
    end if;
    insert into public.sowia_global_notification_preferences(user_id,language,in_app_enabled,updated_at)
    values (auth.uid(),p_language,coalesce(p_in_app_enabled,true),now())
    on conflict (user_id) do update
       set language = excluded.language,
           in_app_enabled = excluded.in_app_enabled,
           updated_at = now();
    return true;
end;
$$;

revoke all on function public.sowia_global_notification_add(uuid,text,uuid) from public, anon, authenticated;
revoke all on function public.sowia_global_notify_connect_request() from public, anon, authenticated;
revoke all on function public.sowia_global_notify_connect_response() from public, anon, authenticated;
revoke all on function public.sowia_global_notify_new_message() from public, anon, authenticated;
revoke all on function public.sowia_global_notifications_mark_read(uuid) from public, anon;
revoke all on function public.sowia_global_notifications_mark_all_read() from public, anon;
revoke all on function public.sowia_global_notification_set_preferences(text,boolean) from public, anon;
grant execute on function public.sowia_global_notifications_mark_read(uuid) to authenticated;
grant execute on function public.sowia_global_notifications_mark_all_read() to authenticated;
grant execute on function public.sowia_global_notification_set_preferences(text,boolean) to authenticated;

comment on table public.sowia_global_notifications is
'Private in-app notifications for GLOBAL CONNECT and GLOBAL MESSENGER events.';

commit;
