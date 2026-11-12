-- SOWIA NIGHT EXCHANGE admin integration queue access test.
-- Run after migration 20261112000200. All temporary settings are transaction-local.
begin;

-- Simulate an ordinary authenticated member. The RPC must reject this claim.
select set_config('request.jwt.claim.sub', '54b7271b-bc5f-4218-bad9-2b53aaa6e90f', true);
select set_config(
    'request.jwt.claims',
    jsonb_build_object(
        'sub', '54b7271b-bc5f-4218-bad9-2b53aaa6e90f',
        'role', 'authenticated',
        'app_metadata', jsonb_build_object('role', 'member')
    )::text,
    true
);
set local role authenticated;

do $$
declare
    v_blocked boolean := false;
begin
    begin
        perform * from public.sowia_admin_list_nex_integrations();
    exception when insufficient_privilege then
        v_blocked := true;
    end;

    if not v_blocked then
        raise exception 'FAIL: unprivileged member accessed the admin queue';
    end if;
    raise notice 'PASS: ordinary member blocked from admin integration queue';
end;
$$;

reset role;

-- Simulate a signed administrator claim and verify that the queue RPC is callable.
select set_config('request.jwt.claim.sub', 'f1792829-ca68-4815-b173-79bd13ce0ed3', true);
select set_config(
    'request.jwt.claims',
    jsonb_build_object(
        'sub', 'f1792829-ca68-4815-b173-79bd13ce0ed3',
        'role', 'authenticated',
        'app_metadata', jsonb_build_object('role', 'admin')
    )::text,
    true
);
set local role authenticated;

select count(*) as "File administrative accessible pour un administrateur"
from public.sowia_admin_list_nex_integrations();

reset role;
rollback;
