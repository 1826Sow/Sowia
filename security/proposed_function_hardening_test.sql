-- SOW IA — proposed TEST-only function hardening review
-- Prepared from read-only inspection of Supabase project SOWIA - TEST.
-- This is a review candidate, NOT an applied migration.
-- Promote into a generated supabase migration only after peer review and TEST validation.

begin;

-- 1) Pin the business-club timestamp trigger function search_path.
-- The function is SECURITY INVOKER and is attached to a BEFORE UPDATE trigger.
create or replace function public.sowia_business_club_set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $function$
begin
    new.updated_at := pg_catalog.now();
    return new;
end;
$function$;

-- 2) Remove API execution paths for the internal event-trigger function.
-- The ensure_rls event trigger itself is retained unchanged.
revoke execute on function public.rls_auto_enable()
    from public, anon, authenticated;

commit;

-- REQUIRED POST-CHANGE VERIFICATION (run separately in SOWIA - TEST):
--
-- A. Verify the timestamp trigger function is pinned:
-- select p.oid::regprocedure, p.proconfig, pg_get_functiondef(p.oid)
-- from pg_catalog.pg_proc p
-- join pg_catalog.pg_namespace n on n.oid = p.pronamespace
-- where n.nspname = 'public'
--   and p.proname = 'sowia_business_club_set_updated_at';
--
-- Expected: proconfig contains search_path="" and the body uses pg_catalog.now().
--
-- B. Verify the internal event-trigger function is no longer callable by API roles:
-- select
--   has_function_privilege('anon', 'public.rls_auto_enable()', 'EXECUTE') as anon_can_execute,
--   has_function_privilege('authenticated', 'public.rls_auto_enable()', 'EXECUTE') as authenticated_can_execute;
--
-- Expected: both false.
--
-- C. Verify the event trigger still enables RLS on newly created public tables.
-- This is a controlled DDL test and MUST run only in the dedicated TEST project:
-- create table public.__sowia_rls_probe (id bigint primary key);
-- select relrowsecurity
-- from pg_catalog.pg_class
-- where oid = 'public.__sowia_rls_probe'::regclass;
-- Expected: true.
-- drop table public.__sowia_rls_probe;
--
-- If step C fails, immediately stop and restore the previous function ACL
-- in TEST before any rollout. Do not promote this change.
--
-- D. Run the existing two-account RLS and Storage integration suites.
-- A skipped job is not a pass. Do not claim multi-account isolation is
-- certified unless the real A/B tests complete successfully.
--
-- INTENTIONALLY NOT CHANGED:
-- - SECURITY DEFINER NEX admin functions: their bodies check app_metadata
--   admin claims; they are intended authenticated admin RPCs.
-- - NEX offer create/respond functions: they require auth.uid(), Premium,
--   ownership/recipient validation, and approved Professional applications.
--   Their authenticated EXECUTE grants are part of the current workflow.
-- - Production, payments, and the existing ensure_rls event trigger.
