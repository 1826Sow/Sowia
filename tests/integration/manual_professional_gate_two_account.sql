-- Manual no-third-email test for the Professional RLS gate.
-- Run ONLY in the dedicated SOW IA TEST project, never production.
-- Replace the UUID below with Premium test account A's auth.users.id.
-- This script temporarily removes A's Premium entitlement/subscription inside
-- one transaction, assumes the authenticated role, tests Personal/Professional
-- access, and ROLLS BACK every change (including the temporary entitlement removal).
--
-- Expected result: the script completes and ends with ROLLBACK.
-- Any failed assertion raises an error; do not replace ROLLBACK with COMMIT.

begin;

-- Replace this placeholder with the UUID of Premium test account A.
-- Set the authenticated JWT context without returning intermediate result grids.
do $claims$
begin
    perform set_config(
        'request.jwt.claim.sub',
        'f1792829-ca68-4815-b173-79bd13ce0ed3',
        true
    );
    perform set_config(
        'request.jwt.claims',
        jsonb_build_object(
            'sub', 'f1792829-ca68-4815-b173-79bd13ce0ed3',
            'role', 'authenticated',
            'aud', 'authenticated'
        )::text,
        true
    );
end;
$claims$;

-- Verify that A is currently Premium, then temporarily remove only A's
-- entitlement records. The final ROLLBACK restores them exactly.
do $precondition$
declare
    test_user_id uuid := auth.uid();
    had_active_entitlement boolean := false;
    had_active_subscription boolean := false;
begin
    if test_user_id is null then
        raise exception 'STOP: replace the UUID placeholder with account A auth.users.id';
    end if;

    if exists (
        select 1 from pg_attribute
        where attrelid = 'public.sowia_entitlements'::regclass
          and attname = 'plan'
          and not attisdropped
    ) then
        execute
            'select exists (
                select 1 from public.sowia_entitlements
                where user_id = $1
                  and plan = ''premium''
                  and status = ''active''
                  and provider = ''paypal''
            )'
        into had_active_entitlement
        using test_user_id;
    else
        select exists (
            select 1 from public.sowia_entitlements
            where user_id = test_user_id
              and status = 'active'
              and provider = 'paypal'
        ) into had_active_entitlement;
    end if;

    if to_regclass('public.sowia_subscriptions') is not null then
        execute
            'select exists (
                select 1 from public.sowia_subscriptions
                where user_id = $1 and status = ''active''
            )'
        into had_active_subscription
        using test_user_id;
    end if;

    if not (had_active_entitlement or had_active_subscription) then
        raise exception 'STOP: account A has no active Premium entitlement to temporarily suspend';
    end if;

    delete from public.sowia_entitlements where user_id = test_user_id;

    if to_regclass('public.sowia_subscriptions') is not null then
        execute 'delete from public.sowia_subscriptions where user_id = $1'
        using test_user_id;
    end if;
end;
$precondition$;

-- Exercise the same database role and JWT claim context as an authenticated
-- user. No third Auth user, email, password, service-role key, or PayPal call.
set local role authenticated;

do $assertions$
declare
    test_user_id uuid := auth.uid();
    marker text := 'SOWIA MANUAL RLS TEST ' || gen_random_uuid()::text;
begin
    if test_user_id is null then
        raise exception 'FAIL: auth.uid() did not resolve the test account';
    end if;

    if public.sowia_has_professional_access() then
        raise exception 'FAIL: account still has Professional access after temporary entitlement removal';
    end if;

    -- Personal workspace must remain usable.
    insert into public.sowia_messages
        (user_id, session_id, role, content, workspace_id)
    values
        (test_user_id, marker, 'user', marker, 'personal');

    insert into public.sowia_memory_items
        (user_id, content, workspace_id)
    values
        (test_user_id, marker, 'personal');

    -- Each Professional INSERT must fail specifically because of RLS.
    begin
        insert into public.sowia_messages
            (user_id, session_id, role, content, workspace_id)
        values
            (test_user_id, marker || ' professional', 'user', marker, 'professional');
        raise exception 'FAIL: free account inserted a Professional message';
    exception when insufficient_privilege then
        null;
    end;

    begin
        insert into public.sowia_memory_items
            (user_id, content, workspace_id)
        values
            (test_user_id, marker || ' professional memory', 'professional');
        raise exception 'FAIL: free account inserted Professional memory';
    exception when insufficient_privilege then
        null;
    end;


    -- Assertions completed. The visible PASS row is emitted after this block.
end;
$assertions$;

-- Return a visible result row in Supabase's Results grid (easier to find on mobile).
select 'PASS: Personal message and memory inserts allowed; Professional message and memory inserts denied.' as validation_result;

-- Mandatory: restore account A's Premium records and remove all test rows.
rollback;
