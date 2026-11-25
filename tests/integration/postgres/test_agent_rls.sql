\set ON_ERROR_STOP on
-- Apply the exact committed migration chain against an isolated PostgreSQL service.
\ir ../../../supabase/migrations/20261125150000_sowia_agent_private_memory.sql
\ir ../../../supabase/migrations/20261125153000_sowia_agent_usage_quota.sql
\ir ../../../supabase/migrations/20261125160000_sowia_agent_tool_permissions_activity.sql
\ir ../../../supabase/migrations/20261125170000_sowia_agent_conversation_history.sql

-- Owner A creates an agent, memory, conversation, message and quota event.
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

-- Switch JWT subject to owner B. RLS must hide A's rows and reject forged inserts.
select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',false);
do $$
begin
  if (select count(*) from public.sowia_agents) <> 0 then
    raise exception 'RLS FAILURE: owner B can read owner A agents';
  end if;
  if (select count(*) from public.sowia_agent_memory_items) <> 0 then
    raise exception 'RLS FAILURE: owner B can read owner A memories';
  end if;
  if (select count(*) from public.sowia_agent_conversations) <> 0 then
    raise exception 'RLS FAILURE: owner B can read owner A conversations';
  end if;
  if (select count(*) from public.sowia_agent_messages) <> 0 then
    raise exception 'RLS FAILURE: owner B can read owner A messages';
  end if;
  begin
    insert into public.sowia_agents(user_id,workspace_id,name)
    values ('11111111-1111-4111-8111-111111111111','personal','Forged agent');
    raise exception 'RLS FAILURE: owner B inserted an agent for owner A';
  exception when insufficient_privilege then
    null;
  end;
  begin
    insert into public.sowia_agent_messages(conversation_id,user_id,agent_id,workspace_id,role,content)
    values ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb','11111111-1111-4111-8111-111111111111','aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','personal','assistant','Forged');
    raise exception 'RLS FAILURE: owner B inserted a message into owner A conversation';
  exception when insufficient_privilege then
    null;
  end;
end
$$;
reset role;
select 'PASS: four migrations applied; owner isolation verified for agents, memories, conversations and messages' as result;
