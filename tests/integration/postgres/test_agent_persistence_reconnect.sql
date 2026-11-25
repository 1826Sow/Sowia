\set ON_ERROR_STOP on
-- This script runs in a fresh psql connection after the migration/test session ends.
set role authenticated;
select set_config('request.jwt.claim.sub','11111111-1111-4111-8111-111111111111',false);
do $$
begin
  if (select count(*) from public.sowia_agents where id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') <> 1 then
    raise exception 'PERSISTENCE FAILURE: agent missing after reconnect';
  end if;
  if (select count(*) from public.sowia_agent_memory_items where content = 'Mémoire privée A') <> 1 then
    raise exception 'PERSISTENCE FAILURE: private memory missing after reconnect';
  end if;
  if (select count(*) from public.sowia_agent_conversations where id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') <> 1 then
    raise exception 'PERSISTENCE FAILURE: conversation missing after reconnect';
  end if;
  if (select count(*) from public.sowia_agent_messages where conversation_id = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb') <> 1 then
    raise exception 'PERSISTENCE FAILURE: message missing after reconnect';
  end if;
end
$$;
select set_config('request.jwt.claim.sub','22222222-2222-4222-8222-222222222222',false);
do $$
begin
  if (select count(*) from public.sowia_agents) <> 0
     or (select count(*) from public.sowia_agent_memory_items) <> 0
     or (select count(*) from public.sowia_agent_conversations) <> 0
     or (select count(*) from public.sowia_agent_messages) <> 0 then
    raise exception 'PERSISTENCE/RLS FAILURE: another owner can read persisted agent data';
  end if;
end
$$;
reset role;
select 'PASS: agent, private memory, conversation and messages persist across a new database connection' as result;
