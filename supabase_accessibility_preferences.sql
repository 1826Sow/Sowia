-- Persistent accessibility preferences for SOW IA accounts.
-- Safe to re-run; existing language preferences are preserved.
alter table public.sowia_user_preferences
    add column if not exists accessibility jsonb not null default
    '{"voice_readout": false, "large_text": false, "high_contrast": false}'::jsonb;

alter table public.sowia_user_preferences
    drop constraint if exists sowia_user_preferences_accessibility_object;

alter table public.sowia_user_preferences
    add constraint sowia_user_preferences_accessibility_object
    check (jsonb_typeof(accessibility) = 'object');

comment on column public.sowia_user_preferences.accessibility is
    'Account-scoped accessibility settings: voice_readout, large_text, high_contrast.';
