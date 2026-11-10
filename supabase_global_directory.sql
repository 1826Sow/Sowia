-- SOWIA GLOBAL DIRECTORY: searchable public categories and specialties.
-- Apply AFTER supabase_global_id.sql.
begin;

alter table public.sowia_global_profiles
    add column if not exists professional_sectors text[] not null default '{}',
    add column if not exists specialties text[] not null default '{}';

alter table public.sowia_global_profiles
    drop constraint if exists sowia_global_profiles_sectors_valid;
alter table public.sowia_global_profiles
    add constraint sowia_global_profiles_sectors_valid check (
        pg_catalog.cardinality(professional_sectors) <= 14
        and professional_sectors <@ array[
            'technology','ai_data','commerce','finance','health_wellness',
            'education','food_agriculture','travel_tourism','media_creative',
            'industry_logistics','environment_energy','professional_services',
            'nonprofit_development','other'
        ]::text[]
    );

alter table public.sowia_global_profiles
    drop constraint if exists sowia_global_profiles_specialties_valid;
alter table public.sowia_global_profiles
    add constraint sowia_global_profiles_specialties_valid check (
        pg_catalog.cardinality(specialties) <= 12
        and pg_catalog.length(pg_catalog.array_to_string(specialties, ',')) <= 720
        and pg_catalog.array_position(specialties, '') is null
    );

create index if not exists sowia_global_profiles_directory_country_idx
    on public.sowia_global_profiles(country) where is_published = true;
create index if not exists sowia_global_profiles_directory_sectors_idx
    on public.sowia_global_profiles using gin(professional_sectors) where is_published = true;
create index if not exists sowia_global_profiles_directory_languages_idx
    on public.sowia_global_profiles using gin(languages) where is_published = true;

create or replace view public.sowia_global_profiles_public
with (security_barrier = true, security_invoker = false)
as
select public_id, display_name, app_name, organization, country, languages,
       website, short_description, verification_status,
       professional_sectors, specialties
from public.sowia_global_profiles
where is_published = true and verification_status <> 'suspended';

revoke all on public.sowia_global_profiles_public from public;
grant select on public.sowia_global_profiles_public to authenticated;

comment on view public.sowia_global_profiles_public is
'Allowlisted public SOWIA directory fields. Only explicitly published and non-suspended profiles are visible; no account identifiers, contact details or verification evidence are exposed.';

commit;
