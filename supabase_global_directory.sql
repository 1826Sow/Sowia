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

create or replace function public.sowia_global_directory_specialties_valid(p_values text[])
returns boolean
language sql
immutable
parallel safe
set search_path = ''
as $
    select pg_catalog.cardinality(coalesce(p_values, array[]::text[])) <= 12
       and coalesce((
           select pg_catalog.bool_and(
               pg_catalog.char_length(pg_catalog.btrim(item)) between 1 and 60
           )
           from pg_catalog.unnest(coalesce(p_values, array[]::text[])) as items(item)
       ), true);
$;

revoke all on function public.sowia_global_directory_specialties_valid(text[]) from public;
grant execute on function public.sowia_global_directory_specialties_valid(text[]) to authenticated;

alter table public.sowia_global_profiles
    drop constraint if exists sowia_global_profiles_specialties_valid;
alter table public.sowia_global_profiles
    add constraint sowia_global_profiles_specialties_valid check (
        public.sowia_global_directory_specialties_valid(specialties)
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
