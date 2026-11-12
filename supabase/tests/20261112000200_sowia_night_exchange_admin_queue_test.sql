-- SOWIA NIGHT EXCHANGE admin integration queue access test.
-- Run after migration 20261112000200. All temporary data is rolled back.
begin;

do $$
declare
    v_a uuid := 'f1792829-ca68-4815-b173-79bd13ce0ed3';
    v_b uuid := '54b7271b-bc5f-4218-bad9-2b53aaa6e90f';
    v_result record;
    v_blocked boolean := false;
begin
    -- The queue function must reject an ordinary authenticated member.
    perform set_config('request.jwt.claim.sub', v_b::text, true);
    perform set_config('request.jwt.claims',
        jsonb_build_object('sub', v_b, 'role', 'authenticated',
                           'app_metadata', jsonb_build_object('role', 'member'))::text, true);
    execute 'set local role authenticated';
    begin
        perform * from public.sowia_admin_list_nex_integrations();
    exception when insufficient_privilege then
        v_blocked := true;
    end;
    reset role;
    if not v_blocked then
        raise exception 'FAIL: unprivileged member accessed the admin queue';
    end if;
    raise notice 'PASS: ordinary member blocked from admin integration queue';
end;
$$;

rollback;
