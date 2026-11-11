-- SOWIA GLOBAL ACTION GOVERNANCE
-- Append-only audit log. A second authenticated account must approve a submitted plan.
begin;
create table if not exists public.sowia_global_action_plans (
    id uuid primary key default gen_random_uuid(),
    creator_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(btrim(title)) between 1 and 160),
    objective text not null check (char_length(btrim(objective)) between 1 and 2000),
    country text not null check (char_length(btrim(country)) between 1 and 100),
    owner_label text not null check (char_length(btrim(owner_label)) between 1 and 120),
    budget_cap numeric(14,2) not null check (budget_cap between 0 and 1000000000),
    currency text not null check (currency in ('EUR','USD','CNY','SGD','MYR','TWD','KRW','XOF','AED','CHF','BRL')),
    due_date date not null,
    success_metric text not null check (char_length(btrim(success_metric)) between 1 and 500),
    stop_condition text not null check (char_length(btrim(stop_condition)) between 1 and 500),
    approver_id uuid not null references auth.users(id),
    status text not null default 'draft' check (status in ('draft','submitted','approved','rejected','completed','cancelled')),
    approval_note text not null default '' check (char_length(approval_note) <= 1000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    approved_at timestamptz,
    constraint sowia_action_no_self_approval check (approver_id is null or approver_id <> creator_id)
);
create table if not exists public.sowia_global_action_audit (
    id uuid primary key default gen_random_uuid(),
    plan_id uuid not null references public.sowia_global_action_plans(id) on delete cascade,
    actor_id uuid not null references auth.users(id),
    from_status text,
    to_status text not null,
    note text not null default '' check (char_length(note) <= 1000),
    created_at timestamptz not null default now()
);
alter table public.sowia_global_action_plans enable row level security;
alter table public.sowia_global_action_audit enable row level security;
drop policy if exists sowia_action_plan_select on public.sowia_global_action_plans;
create policy sowia_action_plan_select on public.sowia_global_action_plans
for select to authenticated using (creator_id = auth.uid() or approver_id = auth.uid());
drop policy if exists sowia_action_audit_select on public.sowia_global_action_audit;
create policy sowia_action_audit_select on public.sowia_global_action_audit
for select to authenticated using (exists (
    select 1 from public.sowia_global_action_plans p where p.id = plan_id
    and (p.creator_id = auth.uid() or p.approver_id = auth.uid())
));
revoke all on public.sowia_global_action_plans, public.sowia_global_action_audit from anon, public;
grant select, insert on public.sowia_global_action_plans to authenticated;
grant select on public.sowia_global_action_audit to authenticated;
drop policy if exists sowia_action_plan_insert on public.sowia_global_action_plans;
create policy sowia_action_plan_insert on public.sowia_global_action_plans
for insert to authenticated with check (creator_id = auth.uid() and status = 'draft' and approver_id <> creator_id);
create or replace function public.sowia_action_transition(p_plan_id uuid, p_next_status text, p_note text default '')
returns void language plpgsql security definer set search_path = '' as $
declare p public.sowia_global_action_plans%rowtype;
declare actor uuid := auth.uid();
begin
 if actor is null then raise exception 'Authentication required'; end if;
 select * into p from public.sowia_global_action_plans where id = p_plan_id for update;
 if not found then raise exception 'Plan not found'; end if;
 if char_length(coalesce(p_note,'')) > 1000 then raise exception 'Note too long'; end if;
 if p.status = 'draft' and p_next_status = 'submitted' and p.creator_id = actor then
   update public.sowia_global_action_plans set status='submitted', updated_at=now() where id=p.id;
 elsif p.status = 'submitted' and p_next_status in ('approved','rejected') and p.approver_id = actor and p.creator_id <> actor then
   update public.sowia_global_action_plans set status=p_next_status,
     approval_note=coalesce(p_note,''), approved_at=case when p_next_status='approved' then now() else null end,
     updated_at=now() where id=p.id;
 elsif p.status = 'approved' and p_next_status='completed' and p.creator_id=actor then
   update public.sowia_global_action_plans set status='completed', updated_at=now() where id=p.id;
 elsif p.status in ('draft','submitted','approved') and p_next_status='cancelled' and p.creator_id=actor then
   update public.sowia_global_action_plans set status='cancelled', updated_at=now() where id=p.id;
 else raise exception 'Transition not permitted'; end if;
 insert into public.sowia_global_action_audit(plan_id,actor_id,from_status,to_status,note)
 values(p.id,actor,p.status,p_next_status,coalesce(p_note,''));
end; $$;
revoke all on function public.sowia_action_transition(uuid,text,text) from public, anon;
grant execute on function public.sowia_action_transition(uuid,text,text) to authenticated;
create index if not exists sowia_action_plans_creator_status_idx on public.sowia_global_action_plans(creator_id,status,created_at desc);
create index if not exists sowia_action_audit_plan_created_idx on public.sowia_global_action_audit(plan_id,created_at);
commit;
