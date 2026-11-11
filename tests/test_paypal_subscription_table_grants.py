from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBSCRIPTIONS = (ROOT / "supabase/migrations/20261109000100_sowia_subscriptions.sql").read_text(encoding="utf-8").lower()
CATALOG = (ROOT / "supabase/migrations/20261109000200_sowia_paypal_catalog.sql").read_text(encoding="utf-8").lower()


def test_subscription_rows_are_read_only_to_authenticated_clients():
    normalized = " ".join(SUBSCRIPTIONS.split())
    assert "alter table public.sowia_subscriptions enable row level security" in normalized
    assert "using (auth.uid() = user_id)" in normalized
    assert "revoke all on public.sowia_subscriptions from anon, authenticated" in normalized
    assert "grant select on public.sowia_subscriptions to authenticated" in normalized
    assert "grant insert on public.sowia_subscriptions to authenticated" not in normalized
    assert "grant update on public.sowia_subscriptions to authenticated" not in normalized
    assert "grant delete on public.sowia_subscriptions to authenticated" not in normalized


def test_paypal_catalog_is_not_accessible_to_browser_roles():
    normalized = " ".join(CATALOG.split())
    assert "alter table public.sowia_paypal_catalog enable row level security" in normalized
    assert "revoke all on public.sowia_paypal_catalog from anon, authenticated" in normalized
    assert "grant select on public.sowia_paypal_catalog to authenticated" not in normalized
    assert "grant insert on public.sowia_paypal_catalog to authenticated" not in normalized
    assert "grant update on public.sowia_paypal_catalog to authenticated" not in normalized
    assert "grant delete on public.sowia_paypal_catalog to authenticated" not in normalized
