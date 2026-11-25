\set ON_ERROR_STOP on
-- Security-contract assertions for the agent schema. Runs only in the ephemeral CI database.
do $$
declare
    v_table text;
    v_function regprocedure;
    v_tables text[] := array[
        'sowia_agents',
        'sowia_agent_memory_items',
        'sowia_agent_usage_monthly',
        'sowia_agent_usage_events',
        'sowia_agent_activity_events',
        'sowia_agent_conversations',
        'sowia_agent_messages'
    ];
    v_functions regprocedure[] := array[
        'public.sowia_get_agent_usage()'::regprocedure,
        'public.sowia_consume_agent_credits(uuid,text)'::regprocedure,
        'public.sowia_consume_agent_action_for_agent(uuid,text,uuid,text,text)'::regprocedure,
        'public.sowia_finish_agent_action_for_agent(uuid,uuid,text,text)'::regprocedure,
        'public.sowia_get_agent_activity(uuid,integer)'::regprocedure
    ];
begin
    foreach v_table in array v_tables loop
        if not coalesce((
            select c.relrowsecurity
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relname = v_table
        ), false) then
            raise exception 'SECURITY FAILURE: RLS is not enabled on public.%', v_table;
        end if;
        if has_table_privilege('anon', format('public.%I', v_table), 'SELECT')
           or has_table_privilege('anon', format('public.%I', v_table), 'INSERT')
           or has_table_privilege('anon', format('public.%I', v_table), 'UPDATE')
           or has_table_privilege('anon', format('public.%I', v_table), 'DELETE') then
            raise exception 'SECURITY FAILURE: anon has direct table access to public.%', v_table;
        end if;
    end loop;

    if has_table_privilege('authenticated', 'public.sowia_agent_usage_monthly', 'SELECT')
       or has_table_privilege('authenticated', 'public.sowia_agent_usage_monthly', 'INSERT')
       or has_table_privilege('authenticated', 'public.sowia_agent_usage_monthly', 'UPDATE')
       or has_table_privilege('authenticated', 'public.sowia_agent_usage_events', 'SELECT')
       or has_table_privilege('authenticated', 'public.sowia_agent_usage_events', 'INSERT')
       or has_table_privilege('authenticated', 'public.sowia_agent_activity_events', 'SELECT')
       or has_table_privilege('authenticated', 'public.sowia_agent_activity_events', 'INSERT') then
        raise exception 'SECURITY FAILURE: authenticated has direct access to private quota/activity ledgers';
    end if;

    foreach v_function in array v_functions loop
        if has_function_privilege('anon', v_function, 'EXECUTE') then
            raise exception 'SECURITY FAILURE: anon can execute %', v_function;
        end if;
        if not has_function_privilege('authenticated', v_function, 'EXECUTE') then
            raise exception 'SECURITY FAILURE: authenticated cannot execute %', v_function;
        end if;
        if exists (
            select 1
            from pg_proc p
            cross join lateral aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
            where p.oid = v_function
              and a.grantee = 0
              and a.privilege_type = 'EXECUTE'
        ) then
            raise exception 'SECURITY FAILURE: PUBLIC can execute %', v_function;
        end if;
    end loop;
end
$$;

-- A caller without a JWT subject must not be able to use any owner-scoped RPC.
reset role;
set role authenticated;
select set_config('request.jwt.claim.sub', '', false);
do $$
begin
    begin
        perform * from public.sowia_get_agent_usage();
        raise exception 'SECURITY FAILURE: unauthenticated quota read was accepted';
    exception when insufficient_privilege then
        null;
    end;
end
$$;
reset role;
select 'PASS: RLS, direct grants, RPC ACLs and unauthenticated access contract' as result;
