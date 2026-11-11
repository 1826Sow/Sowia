-- Extend database-enforced Premium checks to the remaining private Professional modules.
-- Additive, repeatable, and preserves existing rows and owner/participant policies.
begin;

-- CRM and relationship calendar support both Personal and Professional workspaces.
drop policy if exists "Require Premium for Professional growth leads" on public.sowia_growth_leads;
create policy "Require Premium for Professional growth leads"
    on public.sowia_growth_leads as restrictive for all to authenticated
    using (workspace_id = 'personal' or public.sowia_has_professional_access())
    with check (workspace_id = 'personal' or public.sowia_has_professional_access());

drop policy if exists "Require Premium for Professional relationship events" on public.sowia_relationship_events;
create policy "Require Premium for Professional relationship events"
    on public.sowia_relationship_events as restrictive for all to authenticated
    using (workspace_id = 'personal' or public.sowia_has_professional_access())
    with check (workspace_id = 'personal' or public.sowia_has_professional_access());

-- Business Club is a Professional-only feature. Keep existing opt-in,
-- publication, participant, and ownership policies as additional restrictions.
drop policy if exists "Require Premium for Business Club profiles" on public.sowia_business_club_profiles;
create policy "Require Premium for Business Club profiles"
    on public.sowia_business_club_profiles as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

drop policy if exists "Require Premium for Business Club requests" on public.sowia_business_club_requests;
create policy "Require Premium for Business Club requests"
    on public.sowia_business_club_requests as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

drop policy if exists "Require Premium for Business Club meetings" on public.sowia_business_club_meetings;
create policy "Require Premium for Business Club meetings"
    on public.sowia_business_club_meetings as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());


-- Private Business Club notifications are Premium data too, including after
-- a member's entitlement expires. Trigger inserts remain server-owned.
drop policy if exists "Require Premium for Business Club notifications" on public.sowia_business_club_notifications;
create policy "Require Premium for Business Club notifications"
    on public.sowia_business_club_notifications as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

-- NIGHT EXCHANGE is Professional-only, including approved directory reads
-- and its append-only event history.
drop policy if exists "Require Premium for NIGHT EXCHANGE apps" on public.sowia_night_exchange_apps;
create policy "Require Premium for NIGHT EXCHANGE apps"
    on public.sowia_night_exchange_apps as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

drop policy if exists "Require Premium for NIGHT EXCHANGE events" on public.sowia_night_exchange_events;
create policy "Require Premium for NIGHT EXCHANGE events"
    on public.sowia_night_exchange_events as restrictive for all to authenticated
    using (public.sowia_has_professional_access())
    with check (public.sowia_has_professional_access());

commit;
