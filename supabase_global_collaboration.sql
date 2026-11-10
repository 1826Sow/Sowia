-- SOWIA GLOBAL COLLABORATION HUB
-- Apply after GLOBAL ID + DIRECTORY + CONNECT migrations.
begin;

create table if not exists public.sowia_global_projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(btrim(title)) between 1 and 160),
  objective text not null check (char_length(btrim(objective)) between 1 and 2000),
  country text not null check (char_length(btrim(country)) between 1 and 100),
  target_date date not null,
  success_metric text not null check (char_length(btrim(success_metric)) between 1 and 500),
  description text not null default '' check (char_length(description) <= 2000),
  status text not null default 'draft' check (status in ('draft','invited','active','paused','completed','cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sowia_global_project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.sowia_global_projects(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null default 'contributor' check (role in ('owner','coordinator','contributor','observer')),
  status text not null default 'pending' check (status in ('pending','accepted','declined','removed')),
  invited_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(project_id,user_id)
);

create table if not exists public.sowia_global_project_contributions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.sowia_global_projects(id) on delete cascade,
  contributor_id uuid not null references auth.users(id) on delete cascade,
  contribution_type text not null check (contribution_type in ('financial','time','expertise','technology','network','other')),
  description text not null check (char_length(btrim(description)) between 1 and 1000),
  amount numeric(14,2) check (amount is null or amount > 0),
  currency text check (currency is null or currency in ('EUR','USD','GBP','CHF','CNY','SGD','MYR','TWD','KRW','XOF','AED','BRL')),
  hours numeric(10,2) check (hours is null or hours > 0),
  verification_status text not null default 'declared' check (verification_status in ('declared','evidence_provided','reviewed')),
  created_at timestamptz not null default now(),
  constraint sowia_contribution_financial_fields check (
    (contribution_type = 'financial' and amount is not null and currency is not null and hours is null)
    or (contribution_type <> 'financial' and amount is null and currency is null)
  )
);

create table if not exists public.sowia_global_project_milestones (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.sowia_global_projects(id) on delete cascade,
  created_by uuid not null references auth.users(id),
  title text not null check (char_length(btrim(title)) between 1 and 160),
  owner_label text not null check (char_length(btrim(owner_label)) between 1 and 120),
  due_date date not null,
  status text not null default 'pending' check (status in ('pending','in_progress','blocked','completed','cancelled')),
  description text not null default '' check (char_length(description) <= 1000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sowia_global_project_audit (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.sowia_global_projects(id) on delete cascade,
  actor_id uuid not null references auth.users(id),
  event_type text not null check (char_length(event_type) between 1 and 80),
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.sowia_global_projects enable row level security;
alter table public.sowia_global_project_members enable row level security;
alter table public.sowia_global_project_contributions enable row level security;
alter table public.sowia_global_project_milestones enable row level security;
alter table public.sowia_global_project_audit enable row level security;

revoke all on public.sowia_global_projects, public.sowia_global_project_members,
 public.sowia_global_project_contributions, public.sowia_global_project_milestones,
 public.sowia_global_project_audit from anon, public;
grant select, insert, update on public.sowia_global_projects to authenticated;
grant select on public.sowia_global_project_members, public.sowia_global_project_contributions,
 public.sowia_global_project_milestones, public.sowia_global_project_audit to authenticated;
grant insert on public.sowia_global_project_contributions, public.sowia_global_project_milestones to authenticated;

create or replace function public.sowia_project_is_member(p_project_id uuid)
returns boolean language sql stable security definer set search_path = ''
as $$
 select exists(select 1 from public.sowia_global_project_members m
 where m.project_id=p_project_id and m.user_id=auth.uid() and m.status='accepted')
 or exists(select 1 from public.sowia_global_projects p where p.id=p_project_id and p.owner_id=auth.uid());
$$;

create policy sowia_projects_read_member on public.sowia_global_projects
for select to authenticated using (owner_id=auth.uid() or public.sowia_project_is_member(id));
create policy sowia_projects_insert_owner on public.sowia_global_projects
for insert to authenticated with check (owner_id=auth.uid() and status='draft');
create policy sowia_projects_update_owner on public.sowia_global_projects
for update to authenticated using (owner_id=auth.uid()) with check (owner_id=auth.uid());

create policy sowia_project_members_read on public.sowia_global_project_members
for select to authenticated using (user_id=auth.uid() or public.sowia_project_is_member(project_id));
create policy sowia_project_contributions_read on public.sowia_global_project_contributions
for select to authenticated using (public.sowia_project_is_member(project_id));
create policy sowia_project_contributions_insert on public.sowia_global_project_contributions
for insert to authenticated with check (contributor_id=auth.uid() and public.sowia_project_is_member(project_id));
create policy sowia_project_milestones_read on public.sowia_global_project_milestones
for select to authenticated using (public.sowia_project_is_member(project_id));
create policy sowia_project_milestones_insert on public.sowia_global_project_milestones
for insert to authenticated with check (created_by=auth.uid() and public.sowia_project_is_member(project_id));
create policy sowia_project_audit_read on public.sowia_global_project_audit
for select to authenticated using (public.sowia_project_is_member(project_id));

-- Create project and owner membership atomically.
create or replace function public.sowia_global_project_create(
 p_title text,p_objective text,p_country text,p_target_date date,p_success_metric text,p_description text default ''
) returns uuid language plpgsql security definer set search_path = ''
as $$
declare v_id uuid;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 insert into public.sowia_global_projects(owner_id,title,objective,country,target_date,success_metric,description)
 values(auth.uid(),btrim(p_title),btrim(p_objective),btrim(p_country),p_target_date,btrim(p_success_metric),left(coalesce(p_description,''),2000))
 returning id into v_id;
 insert into public.sowia_global_project_members(project_id,user_id,role,status,invited_by)
 values(v_id,auth.uid(),'owner','accepted',auth.uid());
 insert into public.sowia_global_project_audit(project_id,actor_id,event_type)
 values(v_id,auth.uid(),'project_created');
 return v_id;
end; $$;

-- Invite only an account with a published, non-suspended GLOBAL ID profile.
create or replace function public.sowia_global_project_invite(p_project_id uuid,p_public_id text,p_role text default 'contributor')
returns uuid language plpgsql security definer set search_path = ''
as $$
declare v_target uuid; v_member uuid;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 if p_role not in ('coordinator','contributor','observer') then raise exception 'Invalid role'; end if;
 if not (exists(select 1 from public.sowia_global_projects p where p.id=p_project_id and p.owner_id=auth.uid())
  or exists(select 1 from public.sowia_global_project_members m where m.project_id=p_project_id and m.user_id=auth.uid() and m.status='accepted' and m.role in ('owner','coordinator'))) then
  raise exception 'Project invitation not permitted';
 end if;
 select user_id into v_target from public.sowia_global_profiles
 where public_id=p_public_id and is_published=true and verification_status <> 'suspended' limit 1;
 if v_target is null or v_target=auth.uid() then raise exception 'Target profile unavailable'; end if;
 insert into public.sowia_global_project_members(project_id,user_id,role,status,invited_by)
 values(p_project_id,v_target,p_role,'pending',auth.uid())
 on conflict(project_id,user_id) do update set role=excluded.role,status='pending',invited_by=auth.uid(),updated_at=now()
 returning id into v_member;
 insert into public.sowia_global_project_audit(project_id,actor_id,event_type,details)
 values(p_project_id,auth.uid(),'member_invited',jsonb_build_object('role',p_role));
 update public.sowia_global_projects set status='invited',updated_at=now()
 where id=p_project_id and status='draft';
 return v_member;
end; $$;

create or replace function public.sowia_global_project_respond(p_member_id uuid,p_decision text)
returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_project uuid; v_rows integer;
begin
 if auth.uid() is null or p_decision not in ('accepted','declined') then raise exception 'Invalid response'; end if;
 update public.sowia_global_project_members set status=p_decision,updated_at=now()
 where id=p_member_id and user_id=auth.uid() and status='pending' returning project_id into v_project;
 get diagnostics v_rows=row_count;
 if v_rows=1 then
  insert into public.sowia_global_project_audit(project_id,actor_id,event_type,details)
  values(v_project,auth.uid(),'invitation_'||p_decision,'{}'::jsonb);
  if p_decision='accepted' then
   update public.sowia_global_projects set status='active',updated_at=now() where id=v_project and status in ('draft','invited');
  end if;
 end if;
 return v_rows=1;
end; $$;

create or replace function public.sowia_global_project_transition(p_project_id uuid,p_status text,p_note text default '')
returns boolean language plpgsql security definer set search_path = ''
as $$
declare v_old text; v_rows integer;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 if p_status not in ('active','paused','completed','cancelled') or char_length(coalesce(p_note,''))>1000 then raise exception 'Invalid transition'; end if;
 select status into v_old from public.sowia_global_projects where id=p_project_id and owner_id=auth.uid() for update;
 if v_old is null then raise exception 'Project not found or owner access required'; end if;
 if v_old in ('completed','cancelled') then raise exception 'Project is closed'; end if;
 update public.sowia_global_projects set status=p_status,updated_at=now() where id=p_project_id;
 insert into public.sowia_global_project_audit(project_id,actor_id,event_type,details)
 values(p_project_id,auth.uid(),'status_changed',jsonb_build_object('from',v_old,'to',p_status,'note',left(coalesce(p_note,''),1000)));
 return true;
end; $$;

revoke all on function public.sowia_project_is_member(uuid) from public,anon;
revoke all on function public.sowia_global_project_create(text,text,text,date,text,text) from public,anon;
revoke all on function public.sowia_global_project_invite(uuid,text,text) from public,anon;
revoke all on function public.sowia_global_project_respond(uuid,text) from public,anon;
revoke all on function public.sowia_global_project_transition(uuid,text,text) from public,anon;
grant execute on function public.sowia_project_is_member(uuid) to authenticated;
grant execute on function public.sowia_global_project_create(text,text,text,date,text,text) to authenticated;
grant execute on function public.sowia_global_project_invite(uuid,text,text) to authenticated;
grant execute on function public.sowia_global_project_respond(uuid,text) to authenticated;
grant execute on function public.sowia_global_project_transition(uuid,text,text) to authenticated;

create index if not exists sowia_global_projects_owner_idx on public.sowia_global_projects(owner_id,created_at desc);
create index if not exists sowia_global_project_members_user_idx on public.sowia_global_project_members(user_id,status,created_at desc);
create index if not exists sowia_global_project_contributions_project_idx on public.sowia_global_project_contributions(project_id,created_at desc);
create index if not exists sowia_global_project_milestones_project_idx on public.sowia_global_project_milestones(project_id,due_date);

commit;
