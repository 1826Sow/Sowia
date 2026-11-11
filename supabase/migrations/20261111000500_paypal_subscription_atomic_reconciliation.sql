-- Serialize PayPal subscription webhook reconciliation per subscription.
-- Prevent concurrent refund/recovery events from overwriting payment_review.
begin;

create or replace function public.sowia_reconcile_paypal_subscription(
    p_user_id uuid,
    p_paypal_subscription_id text,
    p_paypal_plan_id text,
    p_event_type text,
    p_status text,
    p_currency text,
    p_amount numeric,
    p_next_billing_time timestamptz,
    p_last_payment_at timestamptz,
    p_recovery_verified boolean
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_existing_status text;
    v_effective_status text;
begin
    if p_user_id is null
       or p_paypal_subscription_id is null
       or p_paypal_plan_id is null
       or p_event_type is null
       or p_status is null
       or p_paypal_subscription_id !~ '^I-[A-Z0-9-]{5,64}$'
       or p_paypal_plan_id !~ '^P-[A-Z0-9]+$'
       or p_event_type not in (
           'BILLING.SUBSCRIPTION.ACTIVATED',
           'BILLING.SUBSCRIPTION.UPDATED',
           'BILLING.SUBSCRIPTION.CANCELLED',
           'BILLING.SUBSCRIPTION.SUSPENDED',
           'BILLING.SUBSCRIPTION.EXPIRED',
           'BILLING.SUBSCRIPTION.PAYMENT.FAILED',
           'BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED',
           'PAYMENT.SALE.COMPLETED',
           'PAYMENT.SALE.REFUNDED',
           'PAYMENT.SALE.REVERSED'
       )
       or p_status not in (
           'approval_pending', 'approved', 'active', 'past_due',
           'suspended', 'cancelled', 'expired'
       )
       or (p_amount is not null and (p_amount <= 0 or p_amount <> round(p_amount, 2)))
       or (p_currency is not null and p_currency <> 'EUR')
       or p_recovery_verified is distinct from (
           p_event_type = 'BILLING.SUBSCRIPTION.PAYMENT.SUCCEEDED'
           and p_status = 'active'
       ) then
        raise exception 'Invalid PayPal subscription reconciliation input';
    end if;

    -- Hash-based transaction lock serializes even the first insert, where no
    -- subscription row exists yet for SELECT FOR UPDATE to lock.
    perform pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_paypal_subscription_id, 0)
    );

    select status
      into v_existing_status
      from public.sowia_subscriptions
     where paypal_subscription_id = p_paypal_subscription_id
     for update;

    if p_event_type in ('PAYMENT.SALE.REFUNDED', 'PAYMENT.SALE.REVERSED')
       or (v_existing_status = 'payment_review' and not p_recovery_verified) then
        v_effective_status := 'payment_review';
    else
        v_effective_status := p_status;
    end if;

    insert into public.sowia_subscriptions (
        user_id, provider, paypal_subscription_id, paypal_plan_id, status,
        currency, amount, next_billing_time, last_payment_at, updated_at
    ) values (
        p_user_id, 'paypal', p_paypal_subscription_id, p_paypal_plan_id,
        v_effective_status, p_currency, p_amount, p_next_billing_time,
        p_last_payment_at, pg_catalog.now()
    )
    on conflict (paypal_subscription_id) do update
       set user_id = excluded.user_id,
           provider = excluded.provider,
           paypal_plan_id = excluded.paypal_plan_id,
           status = v_effective_status,
           currency = excluded.currency,
           amount = excluded.amount,
           next_billing_time = excluded.next_billing_time,
           last_payment_at = excluded.last_payment_at,
           updated_at = pg_catalog.now();

    return v_effective_status;
end;
$$;

revoke all on function public.sowia_reconcile_paypal_subscription(
    uuid, text, text, text, text, text, numeric, timestamptz, timestamptz, boolean
) from public, anon, authenticated;
grant execute on function public.sowia_reconcile_paypal_subscription(
    uuid, text, text, text, text, text, numeric, timestamptz, timestamptz, boolean
) to service_role;

commit;
