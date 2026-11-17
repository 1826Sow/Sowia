-- This SECURITY DEFINER function is a trigger-only helper, not a public RPC.
-- PostgreSQL checks trigger function privileges when the trigger is created.
REVOKE ALL ON FUNCTION public.sowia_global_performance_prepare_insert() FROM PUBLIC, anon, authenticated;
