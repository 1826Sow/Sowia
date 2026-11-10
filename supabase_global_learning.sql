-- SOWIA GLOBAL LEARNING ENGINE
-- Apply after supabase_global_decisions.sql.
create table if not exists public.sowia_global_learning_records (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    decision_id uuid not null references public.sowia_global_decisions(id) on delete cascade,
    baseline_snapshot jsonb not null,
    selected_option text not null check (char_length(btrim(selected_option)) between 1 and 120),
    outcome_score integer not null check (outcome_score between 1 and 5),
    outcome_note text not null default '' check (char_length(outcome_note) <= 2000),
    evidence_reference text not null default '' check (char_length(evidence_reference) <= 500),
    recommendation_alignment boolean,
    evaluated_at timestamptz not null,
    created_at timestamptz not null default now(),
    constraint sowia_global_learning_one_record_per_decision unique (user_id, decision_id),
    constraint sowia_global_learning_snapshot_object check (jsonb_typeof(baseline_snapshot) = 'object')
);

create index if not exists sowia_global_learning_user_created_idx
    on public.sowia_global_learning_records(user_id, created_at desc);

alter table public.sowia_global_learning_records enable row level security;

drop policy if exists sowia_global_learning_select_own on public.sowia_global_learning_records;
create policy sowia_global_learning_select_own
    on public.sowia_global_learning_records for select to authenticated
    using (user_id = auth.uid());

drop policy if exists sowia_global_learning_insert_own on public.sowia_global_learning_records;
create policy sowia_global_learning_insert_own
    on public.sowia_global_learning_records for insert to authenticated
    with check (
        user_id = auth.uid()
        and exists (
            select 1 from public.sowia_global_decisions d
            where d.id = decision_id and d.user_id = auth.uid()
        )
        and baseline_snapshot ? 'ranked_options'
    );

drop policy if exists sowia_global_learning_update_own on public.sowia_global_learning_records;
create policy sowia_global_learning_update_own
    on public.sowia_global_learning_records for update to authenticated
    using (user_id = auth.uid())
    with check (user_id = auth.uid());

drop policy if exists sowia_global_learning_delete_own on public.sowia_global_learning_records;
create policy sowia_global_learning_delete_own
    on public.sowia_global_learning_records for delete to authenticated
    using (user_id = auth.uid());

create or replace function public.sowia_global_learning_protect_snapshot()
returns trigger language plpgsql set search_path = public
as $$
begin
    if new.user_id <> old.user_id
       or new.decision_id <> old.decision_id
       or new.baseline_snapshot <> old.baseline_snapshot
       or new.created_at <> old.created_at then
        raise exception 'Original decision snapshot is immutable';
    end if;
    return new;
end;
$$;

drop trigger if exists sowia_global_learning_immutable_snapshot
    on public.sowia_global_learning_records;
create trigger sowia_global_learning_immutable_snapshot
    before update on public.sowia_global_learning_records
    for each row execute function public.sowia_global_learning_protect_snapshot();

revoke all on public.sowia_global_learning_records from anon;
grant select, insert, update, delete on public.sowia_global_learning_records to authenticated;
