-- SOWIA NIGHT EXCHANGE: keep personal-workspace listings out of the public professional directory.
-- Approved personal listings remain visible to their owner, but not to other authenticated users.
begin;

drop policy if exists "nex_select_approved_or_own"
    on public.sowia_night_exchange_apps;

create policy "nex_select_approved_professional_or_own"
on public.sowia_night_exchange_apps
for select to authenticated
using (
    (status = 'approved' and workspace_id = 'professional')
    or user_id = (select auth.uid())
);

comment on policy "nex_select_approved_professional_or_own"
on public.sowia_night_exchange_apps is
'Only approved professional NIGHT EXCHANGE listings are publicly readable; owners retain access to their own listings in either workspace.';

commit;
