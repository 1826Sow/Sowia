-- NIGHT EXCHANGE: trusted commercial-deal creation from approved partner apps.
-- This migration remains a proposal; it is not applied to production.

alter table public.sowia_nex_deals
    add column if not exists creator_app_id uuid
        references public.sowia_night_exchange_apps(id) on delete restrict,
    add column if not exists counterparty_app_id uuid
        references public.sowia_night_exchange_apps(id) on delete restrict;

create index if not exists sowia_nex_deals_creator_app_recent_idx
    on public.sowia_nex_deals (creator_app_id, created_at desc)
    where creator_app_id is not null;
create index if not exists sowia_nex_deals_counterparty_app_recent_idx
    on public.sowia_nex_deals (counterparty_app_id, created_at desc)
    where counterparty_app_id is not null;

-- A client may read its deals, but all creation must pass through the RPC below.
revoke insert on public.sowia_nex_deals from authenticated;
grant select on public.sowia_nex_deals to authenticated;

create or replace function public.sowia_nex_create_deal(
    p_creator_app_id uuid,
    p_counterparty_app_id uuid,
    p_title text,
    p_description text,
    p_deal_kind text,
    p_agreed_amount numeric,
    p_currency text,
    p_commission_bps integer,
    p_idempotency_key text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_actor uuid := auth.uid();
    v_creator_user uuid;
    v_counterparty_user uuid;
    v_deal_id uuid;
    v_existing public.sowia_nex_deals%rowtype;
    v_amount numeric(18,2);
    v_currency text := upper(btrim(coalesce(p_currency, '')));
begin
    if v_actor is null then
        raise exception 'authentication required' using errcode = '42501';
    end if;

    if p_creator_app_id is null
       or p_counterparty_app_id is null
       or p_creator_app_id = p_counterparty_app_id
       or p_title is null
       or char_length(btrim(p_title)) not between 2 and 160
       or p_description is null
       or char_length(p_description) > 4000
       or p_deal_kind not in ('monetary', 'non_monetary')
       or p_deal_kind is null
       or p_agreed_amount is null
       or p_agreed_amount::text = 'NaN'
       or p_agreed_amount < 0
       or v_currency !~ '^[A-Z]{3}$'
       or p_commission_bps is null
       or p_commission_bps not between 0 and 10000
       or p_idempotency_key is null
       or char_length(p_idempotency_key) not between 16 and 128 then
        raise exception 'invalid commercial deal request' using errcode = '22023';
    end if;

    v_amount := p_agreed_amount::numeric(18,2);
    if p_deal_kind = 'non_monetary' then
        if v_amount <> 0 or p_commission_bps <> 0 then
            raise exception 'non-monetary deals must have zero amount and commission'
                using errcode = '22023';
        end if;
    end if;

    select user_id
      into v_creator_user
      from public.sowia_night_exchange_apps
     where id = p_creator_app_id
       and status = 'approved'
       and workspace_id = 'professional';

    if not found or v_creator_user is distinct from v_actor then
        raise exception 'creator app is not an approved app owned by the caller'
            using errcode = '42501';
    end if;

    select user_id
      into v_counterparty_user
      from public.sowia_night_exchange_apps
     where id = p_counterparty_app_id
       and status = 'approved'
       and workspace_id = 'professional';

    if not found or v_counterparty_user is null or v_counterparty_user = v_actor then
        raise exception 'counterparty app is not an approved app owned by another user'
            using errcode = '42501';
    end if;

    insert into public.sowia_nex_deals (
        created_by,
        counterparty_user_id,
        workspace_id,
        title,
        description,
        status,
        deal_kind,
        agreed_amount,
        currency,
        commission_bps,
        idempotency_key,
        creator_app_id,
        counterparty_app_id
    )
    values (
        v_actor,
        v_counterparty_user,
        'professional',
        btrim(p_title),
        p_description,
        'proposed',
        p_deal_kind,
        v_amount,
        v_currency,
        p_commission_bps,
        p_idempotency_key,
        p_creator_app_id,
        p_counterparty_app_id
    )
    on conflict (created_by, idempotency_key) do nothing
    returning id into v_deal_id;

    if v_deal_id is not null then
        return v_deal_id;
    end if;

    select *
      into v_existing
      from public.sowia_nex_deals
     where created_by = v_actor
       and idempotency_key = p_idempotency_key
     for update;

    if not found
       or v_existing.creator_app_id is distinct from p_creator_app_id
       or v_existing.counterparty_app_id is distinct from p_counterparty_app_id
       or v_existing.title is distinct from btrim(p_title)
       or v_existing.description is distinct from p_description
       or v_existing.deal_kind is distinct from p_deal_kind
       or v_existing.agreed_amount is distinct from v_amount
       or v_existing.currency is distinct from v_currency
       or v_existing.commission_bps is distinct from p_commission_bps then
        raise exception 'idempotency key reused with a different deal request'
            using errcode = '23505';
    end if;

    return v_existing.id;
end;
$$;

revoke all on function public.sowia_nex_create_deal(uuid, uuid, text, text, text, numeric, text, integer, text)
    from public, anon, authenticated;
grant execute on function public.sowia_nex_create_deal(uuid, uuid, text, text, text, numeric, text, integer, text)
    to authenticated;

comment on function public.sowia_nex_create_deal(uuid, uuid, text, text, text, numeric, text, integer, text) is
    'Creates a proposed commercial deal only between approved professional app listings, deriving the counterparty user from the trusted registry. Idempotent and audited by the proposal trigger.';
