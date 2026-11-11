-- SOW IA: harden PayPal refund reconciliation against currency mismatches
-- and protect captures that already have recorded refunds.
-- Additive migration: preserves existing ledger rows and the existing capture lock.
begin;

create or replace function public.sowia_enforce_paypal_refund_capture_limit()
returns trigger
language plpgsql
set search_path = public, pg_temp
as $$
declare
    v_capture_gross numeric(30,12);
    v_capture_currency text;
    v_prior_refunds numeric(30,12);
    v_refund_currency_mismatch boolean;
begin
    -- A capture with child refunds is the anchor for those refunds. Do not
    -- let an update silently detach those refunds from their original capture.
    if tg_op = 'UPDATE'
       and old.provider = 'paypal'
       and old.transaction_type = 'payment'
       and exists (
           select 1
             from public.sowia_financial_transactions r
            where r.user_id = old.user_id
              and r.provider = 'paypal'
              and r.parent_capture_id = old.provider_payment_id
              and r.transaction_type = 'refund'
       )
       and (
           new.user_id is distinct from old.user_id
           or new.provider is distinct from old.provider
           or new.transaction_type is distinct from old.transaction_type
           or new.provider_payment_id is distinct from old.provider_payment_id
       ) then
        raise exception 'PayPal capture identity cannot change while refunds reference it';
    end if;

    if new.provider <> 'paypal' then
        return new;
    end if;

    -- A capture amount/currency cannot be changed to values that invalidate
    -- refunds already recorded against it.
    if new.transaction_type = 'payment' and tg_op = 'UPDATE' then
        select coalesce(sum(r.gross_amount), 0),
               coalesce(bool_or(
                   r.gross_currency is null
                   or btrim(r.gross_currency) = ''
                   or upper(btrim(r.gross_currency)) <> upper(btrim(new.gross_currency))
               ), false)
          into v_prior_refunds, v_refund_currency_mismatch
          from public.sowia_financial_transactions r
         where r.user_id = new.user_id
           and r.provider = 'paypal'
           and r.parent_capture_id = new.provider_payment_id
           and r.transaction_type = 'refund';

        if v_prior_refunds > new.gross_amount then
            raise exception 'Updated PayPal capture amount is below refunds already recorded';
        end if;

        if v_refund_currency_mismatch then
            raise exception 'Updated PayPal capture currency conflicts with refunds already recorded';
        end if;

        return new;
    end if;

    if new.transaction_type <> 'refund' then
        return new;
    end if;

    if new.parent_capture_id is null or btrim(new.parent_capture_id) = '' then
        raise exception 'PayPal refund must reference its parent capture';
    end if;

    -- Lock the parent capture so concurrent refunds cannot exceed its total.
    select gross_amount, gross_currency
      into v_capture_gross, v_capture_currency
      from public.sowia_financial_transactions
     where user_id = new.user_id
       and provider = 'paypal'
       and provider_payment_id = new.parent_capture_id
       and transaction_type = 'payment'
     for update;

    if not found then
        raise exception 'PayPal parent capture not found for this account';
    end if;

    -- SQL comparisons with NULL evaluate to NULL, not TRUE; reject missing
    -- currencies explicitly before comparing normalized currency codes.
    if new.gross_currency is null
       or btrim(new.gross_currency) = ''
       or v_capture_currency is null
       or btrim(v_capture_currency) = '' then
        raise exception 'PayPal refund and parent capture must both have a currency';
    end if;

    if upper(btrim(new.gross_currency)) <> upper(btrim(v_capture_currency)) then
        raise exception 'PayPal refund currency does not match its parent capture';
    end if;

    select coalesce(sum(gross_amount), 0)
      into v_prior_refunds
      from public.sowia_financial_transactions
     where user_id = new.user_id
       and provider = 'paypal'
       and parent_capture_id = new.parent_capture_id
       and transaction_type = 'refund'
       and provider_payment_id <> new.provider_payment_id;

    if v_prior_refunds + new.gross_amount > v_capture_gross then
        raise exception 'Cumulative PayPal refunds exceed the parent capture amount';
    end if;

    return new;
end;
$$;

commit;
