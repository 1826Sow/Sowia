-- Keep the admin-only verification audit policy initplan-friendly.
begin;
drop policy if exists "nex_app_verification_admin_read"
    on public.sowia_nex_app_verification_events;
create policy "nex_app_verification_admin_read"
    on public.sowia_nex_app_verification_events for select to authenticated
    using (
        coalesce((select auth.jwt()) -> 'app_metadata' ->> 'role', '') = 'admin'
        or coalesce((select auth.jwt()) -> 'app_metadata' ->> 'sowia_admin', '') = 'true'
    );
commit;
