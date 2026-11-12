from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREMIUM_SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8").lower()


def test_premium_entitlement_table_has_row_level_security():
    assert "create table if not exists public.sowia_entitlements" in PREMIUM_SCHEMA
    assert "plan text not null default 'free' check (plan in ('free', 'premium'))" in PREMIUM_SCHEMA
    assert "alter table public.sowia_entitlements enable row level security" in PREMIUM_SCHEMA


def test_authenticated_users_can_read_only_their_own_premium_entitlement():
    assert 'create policy "users can read own premium entitlement"' in PREMIUM_SCHEMA
    policy_start = PREMIUM_SCHEMA.index(
        'create policy "users can read own premium entitlement"'
    )
    policy_end = PREMIUM_SCHEMA.index(";", policy_start)
    policy = PREMIUM_SCHEMA[policy_start:policy_end]
    assert "for select to authenticated" in policy
    assert "auth.uid()" in policy
    assert "user_id" in policy

    assert "grant select on public.sowia_entitlements to authenticated" in PREMIUM_SCHEMA
    assert "grant insert on public.sowia_entitlements to authenticated" not in PREMIUM_SCHEMA
    assert "grant update on public.sowia_entitlements to authenticated" not in PREMIUM_SCHEMA
    assert "grant delete on public.sowia_entitlements to authenticated" not in PREMIUM_SCHEMA


def test_premium_entitlement_order_id_is_unique_and_amount_is_positive():
    table_start = PREMIUM_SCHEMA.index("create table if not exists public.sowia_entitlements")
    table_end = PREMIUM_SCHEMA.index(");", table_start)
    table = PREMIUM_SCHEMA[table_start:table_end]
    assert "paypal_order_id text not null unique" in table
    assert "amount numeric(10, 2) not null check (amount > 0)" in table
    assert "currency text not null check (currency = 'eur')" in table
