\set ON_ERROR_STOP on
-- Apply the exact committed migration chain against an isolated PostgreSQL service.
\ir ../../../supabase/migrations/20261125150000_sowia_agent_private_memory.sql
\ir ../../../supabase/migrations/20261125153000_sowia_agent_usage_quota.sql
\ir ../../../supabase/migrations/20261125160000_sowia_agent_tool_permissions_activity.sql
\ir ../../../supabase/migrations/20261125170000_sowia_agent_conversation_history.sql
\ir ../../../supabase/migrations/20261125240000_sowia_agent_data_deletion.sql
\ir ../../../supabase/migrations/20261125250000_sowia_agent_memory_owner_read_when_inactive.sql

-- Owner A creates an agent, memory, conversation, message and initial quota event.
set role authenticated;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',false);
insert into public.sowia_agents(id,user_id,workspace_id,name)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','personal','Agent A');
insert into public.sowia_agent_memory_items(agent_id,user_id,workspace_id,content)
values ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','11111111-1111-4111-8111-111111111111','personal','Mémoire privée A');
insert into public.sowia_agent_conversations(id,user_id,agent_id,workspace_id,title)
values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','Fil A');
insert into public.sowia_agent_messages(conversation_id,user_id,agent_id,workspace_id,role,content)
values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','user','Bonjour');
select * from public.sowia_consume_agent_credits('cccccccc-cccc-4ccc-8ccc-cccccccccccc','chat');

-- Per-agent permission: a disabled memory_write tool must be rejected.
update public.sowia_agents set enabled_tools = array['memory_read']::text[]
where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
do $$
begin
  begin
    perform * from public.sowia_consume_agent_action_for_agent(
      'dddddddd-dddd-4ddd-8ddd-dddddddddddd','tool_execution',
      'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','memory_write'
    );
    raise exception 'PERMISSION FAILURE: disabled memory_write was accepted';
  exception when insufficient_privilege then null;
  end;
end
$$;

-- Re-enable memory_write, consume its quota once, and finish the activity.
update public.sowia_agents set enabled_tools = array['memory_read','memory_write']::text[]
where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
do $$
declare v_result record;
begin
  select * into v_result from public.sowia_consume_agent_action_for_agent(
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee','tool_execution',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','memory_write'
  );
  if not v_result.allowed or v_result.used_credits <> 3 then
    raise exception 'QUOTA FAILURE: expected chat + memory_write to use 3 credits';
  end if;
  if not public.sowia_finish_agent_action_for_agent(
    'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','completed',null
  ) then raise exception 'ACTIVITY FAILURE: could not finish agent action'; end if;
  if (select count(*) from public.sowia_get_agent_activity('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',20)
      where status = 'completed' and tool_name = 'memory_write') <> 1 then
    raise exception 'ACTIVITY FAILURE: completed memory_write not visible to owner';
  end if;
end
$$;

update public.sowia_agents set enabled_tools = array['memory_read','web_search']::text[]
where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
reset role;
update public.sowia_agent_usage_monthly set credits_used = 999
where user_id = '11111111-1111-4111-8111-111111111111'
  and month_start = (date_trunc('month', now() at time zone 'UTC'))::date;
set role authenticated;
do $$
declare v_result record;
begin
  select * into v_result from public.sowia_consume_agent_action_for_agent(
    'ffffffff-ffff-4fff-8fff-ffffffffffff','web_search',
    'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','web_search'
  );
  if v_result.allowed or v_result.reason <> 'quota_exceeded' or v_result.remaining_credits <> 1 then
    raise exception 'QUOTA FAILURE: web_search was not blocked at 999/1000 credits';
  end if;
end
$$;

select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',false);
do $$
begin
  if (select count(*) from public.sowia_agents) <> 0 then raise exception 'RLS FAILURE: owner B can read owner A agents'; end if;
  if (select count(*) from public.sowia_agent_memory_items) <> 0 then raise exception 'RLS FAILURE: owner B can read owner A memories'; end if;
  if (select count(*) from public.sowia_agent_conversations) <> 0 then raise exception 'RLS FAILURE: owner B can read owner A conversations'; end if;
  if (select count(*) from public.sowia_agent_messages) <> 0 then raise exception 'RLS FAILURE: owner B can read owner A messages'; end if;
  begin
    insert into public.sowia_agents(user_id,workspace_id,name) values ('11111111-1111-4111-8111-111111111111','personal','Forged agent');
    raise exception 'RLS FAILURE: owner B inserted an agent for owner A';
  exception when insufficient_privilege then null; end;
  begin
    insert into public.sowia_agent_messages(conversation_id,user_id,agent_id,workspace_id,role,content)
    values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','assistant','Forged');
    raise exception 'RLS FAILURE: owner B inserted a message into owner A conversation';
  exception when insufficient_privilege then null; end;
end
$$;
do $agent_test$
begin
  if public.sowia_delete_my_agent_conversation('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','personal') then
    raise exception 'DELETE SECURITY FAILURE: owner B deleted owner A conversation';
  end if;
end
$agent_test$;

select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',false);
update public.sowia_agents set status = 'paused' where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
do $agent_test$
begin
  if (select count(*) from public.sowia_agent_memory_items where agent_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') <> 1 then
    raise exception 'MEMORY ACCESS FAILURE: owner cannot read private memory for paused agent';
  end if;
end
$agent_test$;
delete from public.sowia_agent_memory_items where id = (
  select id from public.sowia_agent_memory_items where agent_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa' limit 1
);
do $agent_test$
begin
  if exists (select 1 from public.sowia_agent_memory_items where agent_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') then
    raise exception 'DELETE FAILURE: owner could not delete paused agent memory';
  end if;
end
$agent_test$;
do $agent_test$
begin
  if not public.sowia_delete_my_agent_conversation('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','personal') then
    raise exception 'DELETE FAILURE: owner could not delete own conversation';
  end if;
end
$agent_test$;
do $agent_test$
begin
  if exists (select 1 from public.sowia_agent_conversations where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') then
    raise exception 'DELETE FAILURE: conversation remains after owner deletion';
  end if;
  if exists (select 1 from public.sowia_agent_messages where conversation_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') then
    raise exception 'CASCADE FAILURE: conversation messages were not deleted';
  end if;
end
$agent_test$;
reset role;
select 'PASS: owner-scoped agent memory and conversation deletion, paused-agent memory access and message cascade' as result;
