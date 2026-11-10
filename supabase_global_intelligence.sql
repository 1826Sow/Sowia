-- SOWIA GLOBAL INTELLIGENCE: private, user-owned market assessments.
-- Apply after supabase_global_moderation.sql.
begin;
create table if not exists public.sowia_global_intelligence_assessments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null check (char_length(btrim(name)) between 1 and 120),
    country text not null check (char_length(btrim(country)) between 1 and 100),
    sector text not null check (char_length(btrim(sector)) between 1 and 100),
    scores jsonb not null check (jsonb_typeof(scores) = 'object'),
    weighted_score numeric(5,1) not null check (weighted_score between 20 and 100),
    evidence_level text not null check (evidence_level in ('hypothesis','indicative','documented','verified')),
    source_note text not null default '' check (char_length(source_note) <= 1500),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists sowia_global_intelligence_owner_idx
    on public.sowia_global_intelligence_assessments(user_id, updated_at desc);
alter table public.sowia_global_intelligence_assessments enable row level security;
drop policy if exists sowia_global_intelligence_owner_all on public.sowia_global_intelligence_assessments;
create policy sowia_global_intelligence_owner_all
on public.sowia_global_intelligence_assessments for all to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.sowia_global_intelligence_assessments from anon, public;
grant select, insert, update, delete on public.sowia_global_intelligence_assessments to authenticated;
comment on table public.sowia_global_intelligence_assessments is
'Private per-user strategic market assessments. Scores are user-entered estimates, not independently verified market data.';
commit;
