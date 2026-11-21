-- Prevent premium non-participants from reading other owners' NIGHT EXCHANGE offers.
begin;
drop policy if exists "Require Premium for NIGHT EXCHANGE offers"
    on public.sowia_night_exchange_offers;
drop policy if exists "nex_offers_select_participants"
    on public.sowia_night_exchange_offers;
create policy "nex_offers_select_participants"
    on public.sowia_night_exchange_offers for select to authenticated
    using (
        (select public.sowia_has_professional_access())
        and (
            sender_user_id = (select auth.uid())
            or recipient_user_id = (select auth.uid())
        )
    );
revoke all on public.sowia_night_exchange_offers from anon, authenticated;
grant select on public.sowia_night_exchange_offers to authenticated;
commit;
