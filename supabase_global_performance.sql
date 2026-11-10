-- SOWIA GLOBAL PERFORMANCE & IMPACT
-- Apply after supabase_global_action_governance.sql.
create table if not exists public.sowia_global_performance_observations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    action_plan_id uuid not null references public.sowia_global_action_plans(id) on delete cascade,
    plan_title_snapshot text not null,
    country_snapshot text not null,
    budget_cap_snapshot numeric(14,2) not null check (budget_cap_snapshot >= 0),
    currency_snapshot text not null check (char_length(currency_snapshot) = 3),
    actual_spend_cumulative numeric(14,2) not null check (actual_spend_cumulative >= 0),
    progress_percent numeric(5,2) not null check (progress_percent between 0 and 100),
    metric_name text not null default '' check (char_length(metric_name) <= 120),
    metric_value numeric(18,4),
    metric_unit text not null default '' check (char_length(metric_unit) <= 40),
    social_impact_note text not null default '' check (char_length(social_impact_note) <= 1500),
    environmental_impact_note text not null default '' check (char_length(environmental_impact_note) <= 1500),
    evidence_level text not null check (evidence_level in ('self_reported','documented','independently_verified')),
    evidence_reference text not null default '' check (char_length(evidence_reference) <= 500),
    observation_note text not null default '' check (char_length(observation_note) <= 2000),
    observed_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists sowia_global_performance_user_observed_idx
    on public.sowia_global_performance_observations(user_id, observed_at desc);
create index if not exists sowia_global_performance_plan_observed_idx
    on public.sowia_global_performance_observations(action_plan_id, observed_at desc);

alter table public.sowia_global_performance_observations enable row level security;

drop policy if exists sowia_global_performance_select_own
    on public.sowia_global_performance_observations;
create policy sowia_global_performance_select_own
    on public.sowia_global_performance_observations for select to authenticated
    using (user_id = auth.uid());

drop policy if exists sowia_global_performance_insert_own
    on public.sowia_global_performance_observations;
create policy sowia_global_performance_insert_own
    on public.sowia_global_performance_observations for insert to authenticated
    with check (
        user_id = auth.uid()
        and exists (
            select 1 from public.sowia_global_action_plans p
            where p.id = action_plan_id
              and p.creator_id = auth.uid()
              and p.status in ('approved','completed')
        )
    );

create or replace function public.sowia_global_performance_prepare_insert()
returns trigger language plpgsql security definer set search_path = public
as $$
declare
    source_plan public.sowia_global_action_plans%rowtype;
begin
    select * into source_plan
    from public.sowia_global_action_plans p
    where p.id = new.action_plan_id
      and p.creator_id = new.user_id
      and p.status in ('approved','completed');
    if not found then
        raise exception 'Approved action plan not found for this user';
    end if;
    new.plan_title_snapshot := source_plan.title;
    new.country_snapshot := source_plan.country;
    new.budget_cap_snapshot := source_plan.budget_cap;
    new.currency_snapshot := source_plan.currency;
    return new;
end;
$$;

drop trigger if exists sowia_global_performance_snapshot
    on public.sowia_global_performance_observations;
create trigger sowia_global_performance_snapshot
    before insert on public.sowia_global_performance_observations
    for each row execute function public.sowia_global_performance_prepare_insert();

revoke all on public.sowia_global_performance_observations from anon;
revoke update, delete on public.sowia_global_performance_observations from authenticated;
grant select, insert on public.sowia_global_performance_observations to authenticated;
