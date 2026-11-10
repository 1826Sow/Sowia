-- SOWIA GLOBAL COLLABORATION HUB: post-migration verification
-- Run in Supabase SQL Editor AFTER the four prerequisite migrations and
-- supabase_global_collaboration.sql. This script is read-only.
do $$
declare
  v_table text;
  v_missing text[] := array[]::text[];
  v_unprotected text[] := array[]::text[];
  v_function text;
  v_missing_functions text[] := array[]::text[];
begin
  foreach v_table in array array[
    'sowia_global_projects',
    'sowia_global_project_members',
    'sowia_global_project_contributions',
    'sowia_global_project_milestones',
    'sowia_global_project_audit'
  ] loop
    if to_regclass('public.' || v_table) is null then
      v_missing := array_append(v_missing, v_table);
    elsif not exists (
      select 1
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public'
        and c.relname = v_table
        and c.relrowsecurity
    ) then
      v_unprotected := array_append(v_unprotected, v_table);
    end if;
  end loop;

  foreach v_function in array array[
    'sowia_global_project_create(text,text,text,date,text,text)',
    'sowia_global_project_invite(uuid,text,text)',
    'sowia_global_project_respond(uuid,text)',
    'sowia_global_project_transition(uuid,text,text)',
    'sowia_global_milestone_transition(uuid,text)',
    'sowia_project_can_contribute(uuid)'
  ] loop
    if to_regprocedure('public.' || v_function) is null then
      v_missing_functions := array_append(v_missing_functions, v_function);
    end if;
  end loop;

  if cardinality(v_missing) > 0
     or cardinality(v_unprotected) > 0
     or cardinality(v_missing_functions) > 0 then
    raise exception
      'SOWIA Hub verification failed. Missing tables: %. Tables without RLS: %. Missing functions: %.',
      coalesce(v_missing, array[]::text[]),
      coalesce(v_unprotected, array[]::text[]),
      coalesce(v_missing_functions, array[]::text[]);
  end if;

  raise notice 'SOWIA Global Collaboration Hub: required tables, RLS and RPC functions are present.';
end;
$$;
