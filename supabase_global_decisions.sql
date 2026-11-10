-- SOWIA GLOBAL DECISION ENGINE: private per-user decision analyses.
begin;
create table if not exists public.sowia_global_decisions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 180),
    evidence_level text not null check (evidence_level in ('hypothesis','indicative','documented','verified')),
    context_note text not null default '' check (char_length(context_note) <= 2000),
    criteria jsonb not null check (jsonb_typeof(criteria) = 'array'),
    ranked_options jsonb not null check (jsonb_typeof(ranked_options) = 'array' and jsonb_array_length(ranked_options) between 2 and 5),
    recommended_option text,
    decision_status text not null check (decision_status in ('recommendation','close_call')),
    score_gap numeric(5,1) not null check (score_gap between 0 and 80),
    confidence integer not null check (confidence between 10 and 85),
    interpretation text not null check (char_length(interpretation) <= 500),
    limitations jsonb not null check (jsonb_typeof(limitations) = 'array'),
    created_at timestamptz not null default now()
);
alter table public.sowia_global_decisions enable row level security;
drop policy if exists sowia_global_decisions_owner_all on public.sowia_global_decisions;
create policy sowia_global_decisions_owner_all
on public.sowia_global_decisions for all to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());
revoke all on public.sowia_global_decisions from anon, public;
grant select, insert, delete on public.sowia_global_decisions to authenticated;
create index if not exists sowia_global_decisions_owner_created_idx
on public.sowia_global_decisions(user_id, created_at desc);
comment on table public.sowia_global_decisions is
'Private decision support comparisons. Scores are user-entered judgments; human review is required.';
commit;
