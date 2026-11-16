-- Add indexes for foreign-key columns flagged by Supabase performance advisor.
-- These indexes do not alter row access policies or application data.

create index if not exists sowia_business_club_meetings_invitee_user_id_idx
  on public.sowia_business_club_meetings (invitee_user_id);
create index if not exists sowia_business_club_meetings_organizer_user_id_idx
  on public.sowia_business_club_meetings (organizer_user_id);
create index if not exists sowia_business_club_meetings_recipient_user_id_idx
  on public.sowia_business_club_meetings (recipient_user_id);
create index if not exists sowia_business_club_meetings_request_id_idx
  on public.sowia_business_club_meetings (request_id);
create index if not exists sowia_business_club_requests_profile_id_idx
  on public.sowia_business_club_requests (profile_id);
create index if not exists sowia_memory_items_user_id_idx
  on public.sowia_memory_items (user_id);
create index if not exists sowia_messages_user_id_idx
  on public.sowia_messages (user_id);
create index if not exists sowia_night_exchange_events_app_id_idx
  on public.sowia_night_exchange_events (app_id);
create index if not exists sowia_relationship_events_lead_id_idx
  on public.sowia_relationship_events (lead_id);
