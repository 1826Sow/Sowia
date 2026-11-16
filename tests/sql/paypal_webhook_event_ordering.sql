-- Behavioral regression tests for the actual migration function.
-- Any failed assertion aborts this CI job because psql uses ON_ERROR_STOP.
do $tests$
declare
  u1 uuid := '11111111-1111-4111-8111-111111111111';
  u2 uuid := '22222222-2222-4222-8222-222222222222';
  u3 uuid := '33333333-3333-4333-8333-333333333333';
  v boolean;
  n integer;
  t timestamptz;
  ownership_rejected boolean := false;
begin
  -- Refund blocks access.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-1',u1,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-REFUND-1','PAYMENT.SALE.REFUNDED','2026-11-16T10:00:00Z','SALE-1',true
  );
  if v is distinct from true then raise exception 'refund did not block'; end if;

  -- Older successful payment must not clear a newer refund.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-1',u1,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-OLD-PAY-1','PAYMENT.SALE.COMPLETED','2026-11-16T09:00:00Z','SALE-OLD',false
  );
  if v is distinct from true then raise exception 'old payment removed refund block'; end if;
  select count(*) into n from public.sowia_paypal_subscription_blocks where paypal_subscription_id='SUB-ORDER-1';
  if n <> 1 then raise exception 'refund block missing after stale payment'; end if;

  -- A later, distinct completed sale may recover access.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-1',u1,'PLAN-1','ACTIVE','EUR',9.90,null,now(),now(),
    'EV-NEW-PAY-1','PAYMENT.SALE.COMPLETED','2026-11-16T11:00:00Z','SALE-NEW',false
  );
  if v is distinct from false then raise exception 'later payment did not recover'; end if;
  select count(*) into n from public.sowia_paypal_subscription_blocks where paypal_subscription_id='SUB-ORDER-1';
  if n <> 0 then raise exception 'recovered block row not deleted'; end if;

  -- An older refund arriving after recovery must not recreate the block.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-1',u1,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-LATE-REFUND-1','PAYMENT.SALE.REFUNDED','2026-11-16T10:30:00Z','SALE-OLD',true
  );
  if v is distinct from false then raise exception 'delayed refund recreated block'; end if;
  select count(*) into n from public.sowia_paypal_subscription_blocks where paypal_subscription_id='SUB-ORDER-1';
  if n <> 0 then raise exception 'delayed refund block row exists'; end if;
  select last_paypal_event_created_at into t from public.sowia_subscriptions where paypal_subscription_id='SUB-ORDER-1';
  if t <> '2026-11-16T11:00:00Z'::timestamptz then raise exception 'durable watermark changed after stale event'; end if;

  -- Later lifecycle cancellation blocks; older activation cannot recover it.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-2',u2,'PLAN-1','CANCELLED','EUR',9.90,null,null,now(),
    'EV-CANCEL-2','BILLING.SUBSCRIPTION.CANCELLED','2026-11-16T12:00:00Z','SUB-ORDER-2',true
  );
  if v is distinct from true then raise exception 'cancellation did not block'; end if;
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-2',u2,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-OLD-ACT-2','BILLING.SUBSCRIPTION.ACTIVATED','2026-11-16T11:30:00Z','SUB-ORDER-2',false
  );
  if v is distinct from true then raise exception 'old activation cleared cancellation'; end if;
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-2',u2,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-NEW-ACT-2','BILLING.SUBSCRIPTION.ACTIVATED','2026-11-16T13:00:00Z','SUB-ORDER-2',false
  );
  if v is distinct from false then raise exception 'later activation did not recover'; end if;
  select count(*) into n from public.sowia_paypal_subscription_blocks where paypal_subscription_id='SUB-ORDER-2';
  if n <> 0 then raise exception 'lifecycle block row not deleted'; end if;

  -- Legacy blocks without event chronology fail closed.
  insert into public.sowia_paypal_subscription_blocks(paypal_subscription_id,user_id,source_event_id,blocked_at)
  values ('SUB-LEGACY',u3,'EV-LEGACY',now());
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-LEGACY',u3,'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
    'EV-LEGACY-RECOVERY','PAYMENT.SALE.COMPLETED','2026-11-16T14:00:00Z','SALE-LEGACY',false
  );
  if v is distinct from true then raise exception 'legacy block did not fail closed'; end if;
  select count(*) into n from public.sowia_paypal_subscription_blocks where paypal_subscription_id='SUB-LEGACY';
  if n <> 1 then raise exception 'legacy block was deleted'; end if;

  -- Equal timestamps are stale too and cannot create a new block.
  v := public.sowia_apply_paypal_subscription_event(
    'SUB-ORDER-2',u2,'PLAN-1','CANCELLED','EUR',9.90,null,null,now(),
    'EV-EQUAL-TIME-2','BILLING.SUBSCRIPTION.CANCELLED','2026-11-16T13:00:00Z','SUB-ORDER-2',true
  );
  if v is distinct from false then raise exception 'equal-time event was not rejected'; end if;

  -- A block ledger row cannot be reassigned to another SOW IA user.
  begin
    perform public.sowia_apply_paypal_subscription_event(
      'SUB-ORDER-1','44444444-4444-4444-8444-444444444444'::uuid,
      'PLAN-1','ACTIVE','EUR',9.90,null,null,now(),
      'EV-WRONG-OWNER','PAYMENT.SALE.COMPLETED','2026-11-16T15:00:00Z','SALE-WRONG',false
    );
  exception when raise_exception then
    ownership_rejected := true;
  end;
  if not ownership_rejected then raise exception 'cross-user subscription reassignment was accepted'; end if;
end;
$tests$;

select 'PayPal webhook chronology behavioral tests passed' as result;
