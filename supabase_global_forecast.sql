-- SOWIA GLOBAL STRATEGIC FORECAST: private saved scenario analyses.
begin;
create table if not exists public.sowia_global_forecasts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 180),
    country text not null check (char_length(country) between 1 and 100),
    sector text not null default '' check (char_length(sector) <= 100),
    horizon text not null check (horizon in ('30 jours','90 jours','12 mois')),
    assessment_score numeric(5,1) not null check (assessment_score between 20 and 100),
    confidence integer not null check (confidence between 10 and 85),
    evidence_level text not null check (evidence_level in ('hypothesis','indicative','documented','verified')),
    scenarios jsonb not null check (jsonb_typeof(scenarios) = 'array' and jsonb_array_length(scenarios) = 5),
    assumptions jsonb not null check (jsonb_typeof(assumptions) = 'array'),
    alert_counts jsonb not null default '{}'::jsonb check (jsonb_typeof(alert_counts) = 'object'),
    risk_pressure integer not null default 0 check (risk_pressure between 0 and 100),
    opportunity_signal integer not null default 0 check (opportunity_signal between 0 and 100),
    created_at timestamptz not null default now()
);
alter table public.sowia_global_forecasts enable row level security;
drop policy if exists sowia_global_forecasts_owner_all on public.sowia_global_forecasts;
create policy sowia_global_forecasts_owner_all
on public.sowia_global_forecasts for all to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.sowia_global_forecasts from anon, public;
grant select, insert, delete on public.sowia_global_forecasts to authenticated;
create index if not exists sowia_global_forecasts_owner_created_idx
on public.sowia_global_forecasts(user_id, created_at desc);
comment on table public.sowia_global_forecasts is
'Private user-owned scenario analysis. Scenarios are conditional planning assumptions, not predictions or probabilities.';
commit;
