-- Preserve PayPal event chronology and serialize all access decisions per subscription.
-- Additive columns; legacy block rows are deliberately retained and fail closed.

begin;

alter table public.sowia_paypal_subscription_blocks
  add column if not exists source_event_type text,
  add column if not exists source_event_created_at timestamptz,
  add column if not exists source_resource_id text;

create or replace function public.sowia_apply_paypal_subscription_event(
  p_subscription_id text,
  p_user_id uuid,
  p_plan_id text,
  p_status text,
  p_currency text,
  p_amount numeric,
  p_next_billing_time timestamptz,
  p_last_payment_at timestamptz,
  p_updated_at timestamptz,
  p_event_id text,
  p_event_type text,
  p_event_created_at timestamptz,
  p_resource_id text,
  p_blocked_event boolean
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_block public.sowia_paypal_subscription_blocks%rowtype;
  v_has_block boolean := false;
  v_previously_blocked boolean := false;
  v_incoming_block_is_stale boolean := false;
  v_can_recover boolean := false;
  v_effective_block_event boolean := false;
  v_access_blocked boolean := false;
begin
  if p_subscription_id is null or p_subscription_id = ''
     or p_user_id is null or p_plan_id is null or p_event_id is null
     or p_event_type is null or p_event_created_at is null then
    raise exception 'Required PayPal subscription event fields are missing';
  end if;

  -- Serialize every webhook decision for this subscription, including the
  -- first event when no block-ledger row exists yet.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(p_subscription_id, 0)
  );

  select b.*
    into v_block
    from public.sowia_paypal_subscription_blocks as b
   where b.paypal_subscription_id = p_subscription_id
   for update;

  v_has_block := found;

  select coalesce(s.paypal_access_blocked, false)
    into v_previously_blocked
    from public.sowia_subscriptions as s
   where s.paypal_subscription_id = p_subscription_id
   for update;

  v_previously_blocked := coalesce(v_previously_blocked, false);

  v_incoming_block_is_stale :=
    coalesce(p_blocked_event, false)
    and v_has_block
    and (
      v_block.source_event_created_at is null
      or p_event_created_at <= v_block.source_event_created_at
    );

  v_can_recover :=
    v_has_block
    and v_block.source_event_created_at is not null
    and p_event_created_at > v_block.source_event_created_at
    and (
      (
        v_block.source_event_type in ('PAYMENT.SALE.REFUNDED', 'PAYMENT.SALE.REVERSED')
        and p_event_type = 'PAYMENT.SALE.COMPLETED'
        and p_resource_id is not null
        and p_resource_id <> coalesce(v_block.source_resource_id, '')
      )
      or (
        v_block.source_event_type = 'BILLING.SUBSCRIPTION.PAYMENT.FAILED'
        and p_event_type = 'PAYMENT.SALE.COMPLETED'
      )
      or (
        v_block.source_event_type in (
          'BILLING.SUBSCRIPTION.CANCELLED',
          'BILLING.SUBSCRIPTION.SUSPENDED',
          'BILLING.SUBSCRIPTION.EXPIRED'
        )
        and p_event_type = 'BILLING.SUBSCRIPTION.ACTIVATED'
      )
    );

  v_effective_block_event :=
    coalesce(p_blocked_event, false) and not v_incoming_block_is_stale;

  v_access_blocked :=
    upper(coalesce(p_status, 'UNKNOWN')) <> 'ACTIVE'
    or v_effective_block_event
    or ((v_previously_blocked or v_has_block) and not v_can_recover);

  insert into public.sowia_subscriptions (
    user_id,
    provider,
    paypal_subscription_id,
    paypal_plan_id,
    status,
    paypal_access_blocked,
    currency,
    amount,
    next_billing_time,
    last_payment_at,
    updated_at
  ) values (
    p_user_id,
    'paypal',
    p_subscription_id,
    p_plan_id,
    lower(coalesce(p_status, 'unknown')),
    v_access_blocked,
    p_currency,
    p_amount,
    p_next_billing_time,
    p_last_payment_at,
    coalesce(p_updated_at, pg_catalog.now())
  )
  on conflict (paypal_subscription_id) do update
    set user_id = excluded.user_id,
        provider = excluded.provider,
        paypal_plan_id = excluded.paypal_plan_id,
        status = excluded.status,
        paypal_access_blocked = excluded.paypal_access_blocked,
        currency = excluded.currency,
        amount = excluded.amount,
        next_billing_time = excluded.next_billing_time,
        last_payment_at = excluded.last_payment_at,
        updated_at = excluded.updated_at;

  if v_effective_block_event then
    insert into public.sowia_paypal_subscription_blocks (
      paypal_subscription_id,
      user_id,
      source_event_id,
      source_event_type,
      source_event_created_at,
      source_resource_id,
      blocked_at
    ) values (
      p_subscription_id,
      p_user_id,
      p_event_id,
      p_event_type,
      p_event_created_at,
      p_resource_id,
      pg_catalog.now()
    )
    on conflict (paypal_subscription_id) do update
      set user_id = excluded.user_id,
          source_event_id = excluded.source_event_id,
          source_event_type = excluded.source_event_type,
          source_event_created_at = excluded.source_event_created_at,
          source_resource_id = excluded.source_resource_id,
          blocked_at = excluded.blocked_at;
  elsif v_can_recover and not v_access_blocked then
    delete from public.sowia_paypal_subscription_blocks
     where paypal_subscription_id = p_subscription_id;
  end if;

  return v_access_blocked;
end;
$function$;

revoke all on function public.sowia_apply_paypal_subscription_event(
  text, uuid, text, text, text, numeric, timestamptz, timestamptz,
  timestamptz, text, text, timestamptz, text, boolean
) from public, anon, authenticated;

grant execute on function public.sowia_apply_paypal_subscription_event(
  text, uuid, text, text, text, numeric, timestamptz, timestamptz,
  timestamptz, text, text, timestamptz, text, boolean
) to service_role;

commit;
