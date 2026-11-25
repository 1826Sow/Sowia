-- Keep the low-level quota consumer internal to trusted server-side callers.
-- The public agent entry point remains executable by authenticated users and calls
-- this helper under its SECURITY DEFINER owner context.
begin;

revoke execute on function public.sowia_consume_agent_credits(uuid, text)
from public, anon, authenticated;

commit;
