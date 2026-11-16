begin;

-- Preserve the existing permissive UPDATE semantics by OR-combining
-- both USING predicates and both WITH CHECK predicates.
drop policy if exists "Invitees can respond to club meetings" on public.sowia_business_club_meetings;
drop policy if exists "Organizers can cancel proposed club meetings" on public.sowia_business_club_meetings;
create policy "Club meeting participants can update allowed transitions"
on public.sowia_business_club_meetings
as permissive
for update
to authenticated
using (
  (((select auth.uid()) = invitee_user_id) and status = 'Proposée')
  or
  (((select auth.uid()) = organizer_user_id) and status = 'Proposée')
)
with check (
  (((select auth.uid()) = invitee_user_id) and status in ('Confirmée', 'Refusée'))
  or
  (((select auth.uid()) = organizer_user_id) and status = 'Annulée')
);

drop policy if exists "Recipients can respond to club requests" on public.sowia_business_club_requests;
drop policy if exists "Senders can cancel pending club requests" on public.sowia_business_club_requests;
create policy "Club request participants can update allowed transitions"
on public.sowia_business_club_requests
as permissive
for update
to authenticated
using (
  (((select auth.uid()) = recipient_user_id) and status = 'En attente')
  or
  (((select auth.uid()) = sender_user_id) and status = 'En attente')
)
with check (
  (((select auth.uid()) = recipient_user_id) and status in ('Acceptée', 'Refusée'))
  or
  (((select auth.uid()) = sender_user_id) and status = 'Annulée')
);

drop policy if exists nex_admin_select_all on public.sowia_night_exchange_apps;
drop policy if exists nex_select_approved_or_own on public.sowia_night_exchange_apps;
create policy nex_select_admin_approved_or_own
on public.sowia_night_exchange_apps
as permissive
for select
to authenticated
using (
  coalesce(((select auth.jwt()) -> 'app_metadata' ->> 'role'), '') = 'admin'
  or coalesce(((select auth.jwt()) -> 'app_metadata' ->> 'sowia_admin'), '') = 'true'
  or status = 'approved'
  or user_id = (select auth.uid())
);

commit;
