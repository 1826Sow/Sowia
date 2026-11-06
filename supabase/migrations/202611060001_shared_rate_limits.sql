-- Shared per-account rate limits. Apply ONLY to an isolated Supabase project first.
create table if not exists public.sowia_rate_limits (
    user_id uuid not null references auth.users(id) on delete cascade,
    bucket_key text not null,
    window_started_at timestamptz not null,
    request_count integer not null check (request_count >= 1),
    primary key (user_id, bucket_key),
    constraint sowia_rate_limits_bucket_check check (bucket_key in (
        'assistant', 'pdf_question', 'advanced_pdf', 'batch_pdf',
        'web_search', 'document_upload', 'document_download', 'document_delete'
    ))
);

alter table public.sowia_rate_limits enable row level security;
revoke all on table public.sowia_rate_limits from public, anon, authenticated;

create or replace function public.sowia_consume_rate_limit(p_bucket_key text)
returns table (allowed boolean, remaining integer, reset_at timestamptz)
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    v_user_id uuid := auth.uid();
    v_window_seconds integer;
    v_limit integer;
    v_started_at timestamptz;
    v_count integer;
begin
    if v_user_id is null then
        raise exception 'authentication required' using errcode = '28000';
    end if;

    case p_bucket_key
        when 'assistant' then v_window_seconds := 60; v_limit := 10;
        when 'pdf_question' then v_window_seconds := 60; v_limit := 5;
        when 'advanced_pdf' then v_window_seconds := 300; v_limit := 3;
        when 'batch_pdf' then v_window_seconds := 600; v_limit := 2;
        when 'web_search' then v_window_seconds := 60; v_limit := 5;
        when 'document_upload' then v_window_seconds := 600; v_limit := 5;
        when 'document_download' then v_window_seconds := 60; v_limit := 10;
        when 'document_delete' then v_window_seconds := 60; v_limit := 5;
        else
            raise exception 'invalid rate limit bucket' using errcode = '22023';
    end case;

    insert into public.sowia_rate_limits as current_limit
        (user_id, bucket_key, window_started_at, request_count)
    values (v_user_id, p_bucket_key, clock_timestamp(), 1)
    on conflict (user_id, bucket_key) do update
    set window_started_at = case
            when current_limit.window_started_at
                 + make_interval(secs => v_window_seconds) <= clock_timestamp()
            then clock_timestamp()
            else current_limit.window_started_at
        end,
        request_count = case
            when current_limit.window_started_at
                 + make_interval(secs => v_window_seconds) <= clock_timestamp()
            then 1
            else current_limit.request_count + 1
        end
    returning current_limit.window_started_at, current_limit.request_count
    into v_started_at, v_count;

    allowed := v_count <= v_limit;
    remaining := greatest(v_limit - v_count, 0);
    reset_at := v_started_at + make_interval(secs => v_window_seconds);
    return next;
end;
$function$;

revoke all on function public.sowia_consume_rate_limit(text) from public, anon;
grant execute on function public.sowia_consume_rate_limit(text) to authenticated;

comment on table public.sowia_rate_limits is
    'Private shared per-user rate-limit counters; direct client access is revoked.';
comment on function public.sowia_consume_rate_limit(text) is
    'Atomically consumes a server-defined quota for auth.uid(); callers cannot choose limits.';
