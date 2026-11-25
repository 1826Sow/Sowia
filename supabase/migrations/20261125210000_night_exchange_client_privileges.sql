-- NIGHT EXCHANGE: least-privilege client access hardening.
-- Keep all financial mutations behind the authenticated SECURITY DEFINER RPCs.
-- Revoke Supabase default client table privileges, then restore read-only access
-- only where the existing RLS policies intentionally permit it.
begin;

revoke all privileges on table
  public.sowia_nex_share_classes,
  public.sowia_nex_wallets,
  public.sowia_nex_orders,
  public.sowia_nex_trades,
  public.sowia_nex_ledger,
  public.sowia_nex_positions,
  public.sowia_nex_market_config,
  public.sowia_nex_revenue_ledger
from anon, authenticated;

grant select on table
  public.sowia_nex_share_classes,
  public.sowia_nex_wallets,
  public.sowia_nex_orders,
  public.sowia_nex_trades,
  public.sowia_nex_ledger,
  public.sowia_nex_positions,
  public.sowia_nex_market_config
to authenticated;

-- No direct client access to the internal SOW IA revenue allocation ledger.
-- RLS policies remain the row-level boundary for all SELECT grants.
commit;
