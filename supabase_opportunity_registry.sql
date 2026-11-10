-- SOWIA opportunity register.
-- Apply manually in Supabase SQL Editor after reviewing the project migrations.
create table if not exists public.sowia_opportunity_registry (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    title text not null check (char_length(title) between 1 and 240),
    summary text not null default '' check (char_length(summary) <= 2000),
    country text not null check (char_length(country) between 1 and 100),
    category text not null default '',
    source_url text not null default '',
    status text not null default 'À examiner'
        check (status in ('À examiner','En vérification','À contacter','En discussion','Acceptée','Refusée','Expirée')),
    relevance_score integer not null default 0 check (relevance_score between 0 and 100),
    verification_note text not null default '' check (char_length(verification_note) <= 2000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists sowia_opportunity_registry_owner_updated_idx
    on public.sowia_opportunity_registry (owner_id, updated_at desc);
create unique index if not exists sowia_opportunity_registry_owner_source_uidx
    on public.sowia_opportunity_registry (owner_id, source_url)
    where source_url <> '';

alter table public.sowia_opportunity_registry enable row level security;

drop policy if exists "Users read own SOWIA opportunities" on public.sowia_opportunity_registry;
create policy "Users read own SOWIA opportunities"
    on public.sowia_opportunity_registry for select
    using (auth.uid() = owner_id);

drop policy if exists "Users insert own SOWIA opportunities" on public.sowia_opportunity_registry;
create policy "Users insert own SOWIA opportunities"
    on public.sowia_opportunity_registry for insert
    with check (auth.uid() = owner_id);

drop policy if exists "Users update own SOWIA opportunities" on public.sowia_opportunity_registry;
create policy "Users update own SOWIA opportunities" on public.sowia_opportunity_registry for update
    using (auth.uid() = owner_id)
    with check (auth.uid() = owner_id);

drop policy if exists "Users delete own SOWIA opportunities" on public.sowia_opportunity_registry;
create policy "Users delete own SOWIA opportunities"
    on public.sowia_opportunity_registry for delete
    using (auth.uid() = owner_id);

comment on table public.sowia_opportunity_registry is
    'User-scoped register of public opportunity leads; entries require human verification.';
