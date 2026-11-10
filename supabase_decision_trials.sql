-- Human vs SOW IA strategic decision benchmark.
-- Append-only decision snapshot; outcome evaluation is stored separately.
begin;

create table if not exists public.sowia_decision_trials (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    workspace_id text not null default 'professional'
        check (workspace_id in ('personal','professional')),
    title text not null check (char_length(title) between 1 and 160),
    question text not null check (char_length(question) between 1 and 500),
    context text not null default '',
    category text not null default 'Non classé',
    human_choice text not null,
    ai_choice text,
    ai_rationale text not null,
    options jsonb not null check (jsonb_typeof(options) = 'array'),
    decision_hash text not null check (decision_hash ~ '^[0-9a-f]{64}$'),
    decided_at timestamptz not null,
    outcomes jsonb,
    human_outcome numeric(5,1),
    ai_outcome numeric(5,1),
    winner text,
    outcome_difference numeric(6,1),
    evaluated_at timestamptz,
    created_at timestamptz not null default now(),
    check (human_outcome is null or human_outcome between 0 and 100),
    check (ai_outcome is null or ai_outcome between 0 and 100)
);

alter table public.sowia_decision_trials
    add column if not exists category text not null default 'Non classé';

create index if not exists sowia_decision_trials_user_date_idx
    on public.sowia_decision_trials (user_id, workspace_id, decided_at desc);

alter table public.sowia_decision_trials enable row level security;
drop policy if exists "Users read own SOW IA decision trials" on public.sowia_decision_trials;
create policy "Users read own SOW IA decision trials"
    on public.sowia_decision_trials for select to authenticated
    using ((select auth.uid()) = user_id);
drop policy if exists "Users create own SOW IA decision trials" on public.sowia_decision_trials;
create policy "Users create own SOW IA decision trials"
    on public.sowia_decision_trials for insert to authenticated
    with check ((select auth.uid()) = user_id);
drop policy if exists "Users evaluate own SOW IA decision trials" on public.sowia_decision_trials;
create policy "Users evaluate own SOW IA decision trials"
    on public.sowia_decision_trials for update to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);

revoke all on public.sowia_decision_trials from anon;
grant select, insert, update on public.sowia_decision_trials to authenticated;

-- Prevent later edits to the original sealed human/AI decision.
create or replace function public.sowia_guard_decision_trial_snapshot()
returns trigger language plpgsql set search_path = public, pg_temp as $$
begin
    if new.user_id is distinct from old.user_id
       or new.workspace_id is distinct from old.workspace_id
       or new.title is distinct from old.title
       or new.question is distinct from old.question
       or new.context is distinct from old.context
       or new.human_choice is distinct from old.human_choice
       or new.ai_choice is distinct from old.ai_choice
       or new.ai_rationale is distinct from old.ai_rationale
       or new.options is distinct from old.options
       or new.decision_hash is distinct from old.decision_hash
       or new.decided_at is distinct from old.decided_at then
        raise exception 'The original decision snapshot is immutable';
    end if;
    if old.evaluated_at is not null then
        raise exception 'Decision outcome has already been recorded';
    end if;
    return new;
end;
$$;

drop trigger if exists sowia_decision_trial_snapshot_guard on public.sowia_decision_trials;
create trigger sowia_decision_trial_snapshot_guard
before update on public.sowia_decision_trials
for each row execute function public.sowia_guard_decision_trial_snapshot();

commit;
