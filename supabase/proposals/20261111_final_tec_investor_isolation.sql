-- PROPOSAL ONLY — do not apply to production.
-- FINAL TEC investor data isolation, independent from SOWIA private/financial tables.
-- Place outside supabase/migrations so deployment tooling cannot auto-apply it.

begin;

create table if not exists public.final_tec_investor_access (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    project_key text not null default 'final-tec' check (project_key = 'final-tec'),
    role text not null check (role in ('final_tec_admin', 'final_tec_analyst', 'final_tec_investor_viewer')),
    status text not null default 'pending' check (status in ('pending', 'active', 'revoked', 'expired')),
    starts_at timestamptz not null default now(),
    expires_at timestamptz,
    granted_by uuid references auth.users(id),
    grant_reason text not null,
    revoked_at timestamptz,
    revoked_by uuid references auth.users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint final_tec_access_expiry_after_start check (expires_at is null or expires_at > starts_at),
    constraint final_tec_access_revocation_consistent check (
        (status = 'revoked' and revoked_at is not null)
        or (status <> 'revoked' and revoked_at is null)
    )
);

create index if not exists final_tec_access_user_project_status_idx
    on public.final_tec_investor_access (user_id, project_key, status, expires_at);

create table if not exists public.final_tec_published_metrics (
    id uuid primary key default gen_random_uuid(),
    project_key text not null default 'final-tec' check (project_key = 'final-tec'),
    metric_key text not null,
    title text not null,
    category text not null,
    metric_value jsonb,
    unit text,
    evidence_status text not null check (evidence_status in ('verified', 'projected', 'synthetic', 'pending')),
    source_url text,
    observed_at timestamptz,
    evidence_ref text,
    evidence_owner text,
    assumptions text,
    horizon text,
    synthetic_label text,
    publication_state text not null default 'draft' check (publication_state in ('draft', 'published', 'withdrawn')),
    approved_by uuid references auth.users(id),
    published_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint final_tec_metric_evidence_complete check (
        (evidence_status <> 'verified' or (
            source_url is not null and source_url like 'https://%'
            and observed_at is not null
            and evidence_ref is not null and length(trim(evidence_ref)) > 0
            and evidence_owner is not null and length(trim(evidence_owner)) > 0
        ))
        and (evidence_status <> 'projected' or (
            assumptions is not null and length(trim(assumptions)) > 0
            and horizon is not null and length(trim(horizon)) > 0
        ))
        and (evidence_status <> 'synthetic' or (
            synthetic_label is not null and length(trim(synthetic_label)) > 0
        ))
        and not (publication_state = 'published' and evidence_status = 'pending')
    ),
    constraint final_tec_metric_publish_audit check (
        publication_state <> 'published'
        or (approved_by is not null and published_at is not null)
    )
);

create index if not exists final_tec_metrics_publication_idx
    on public.final_tec_published_metrics (project_key, publication_state, category);

create table if not exists public.final_tec_investor_audit_log (
    id uuid primary key default gen_random_uuid(),
    occurred_at timestamptz not null default now(),
    actor_user_id uuid references auth.users(id),
    project_key text not null default 'final-tec' check (project_key = 'final-tec'),
    action text not null,
    resource_type text,
    resource_id text,
    outcome text not null check (outcome in ('allowed', 'denied', 'changed')),
    reason_code text,
    session_ref text
);

create index if not exists final_tec_audit_time_idx
    on public.final_tec_investor_audit_log (occurred_at desc);

alter table public.final_tec_investor_access enable row level security;
alter table public.final_tec_published_metrics enable row level security;
alter table public.final_tec_investor_audit_log enable row level security;

-- Fail closed: authenticated users receive no direct access to assignments or audit logs.
revoke all on public.final_tec_investor_access from anon, authenticated;
revoke all on public.final_tec_investor_audit_log from anon, authenticated;
revoke all on public.final_tec_published_metrics from anon, authenticated;

-- A narrow SECURITY DEFINER predicate reads the private assignment table.
-- It returns true only for a currently active, unexpired viewer assignment.
create or replace function public.final_tec_can_view_published_metrics()
returns boolean
language sql
stable
security definer
set search_path = pg_catalog, public, auth
as $function$
    select exists (
        select 1
        from public.final_tec_investor_access a
        where a.user_id = auth.uid()
          and a.project_key = 'final-tec'
          and a.role = 'final_tec_investor_viewer'
          and a.status = 'active'
          and a.starts_at <= now()
          and (a.expires_at is null or a.expires_at > now())
    );
$function$;

revoke all on function public.final_tec_can_view_published_metrics() from public;
grant execute on function public.final_tec_can_view_published_metrics() to authenticated;

grant select on public.final_tec_published_metrics to authenticated;

drop policy if exists final_tec_metrics_viewer_select on public.final_tec_published_metrics;
create policy final_tec_metrics_viewer_select
on public.final_tec_published_metrics
for select
to authenticated
using (
    project_key = 'final-tec'
    and publication_state = 'published'
    and public.final_tec_can_view_published_metrics()
);

-- Server-side service role only. No client-side write policy is created.
grant all on public.final_tec_investor_access to service_role;
grant all on public.final_tec_published_metrics to service_role;
grant select, insert on public.final_tec_investor_audit_log to service_role;

commit;
