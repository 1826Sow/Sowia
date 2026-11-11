"""Static regression guards for Premium enforcement across Professional modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase/migrations/20261111000300_sowia_professional_modules_rls.sql"
).read_text(encoding="utf-8").lower()


def test_all_remaining_professional_modules_have_restrictive_premium_policies():
    normalized = " ".join(MIGRATION.split())
    tables = (
        "sowia_growth_leads",
        "sowia_relationship_events",
        "sowia_business_opportunities",
        "sowia_business_club_profiles",
        "sowia_business_club_requests",
        "sowia_business_club_meetings",
        "sowia_business_club_notifications",
        "sowia_night_exchange_apps",
        "sowia_night_exchange_events",
    )
    for table in tables:
        assert f"on public.{table} as restrictive for all to authenticated" in normalized
        assert f"drop policy if exists" in normalized
    assert normalized.count("public.sowia_has_professional_access()") >= 7


def test_personal_rows_remain_available_without_premium_where_supported():
    normalized = " ".join(MIGRATION.split())
    assert normalized.count("workspace_id = 'personal' or public.sowia_has_professional_access()") == 6


def test_business_club_and_night_exchange_remain_professional_only():
    normalized = " ".join(MIGRATION.split())
    for table in ("sowia_business_club_profiles", "sowia_business_club_requests", "sowia_business_club_meetings", "sowia_business_club_notifications", "sowia_night_exchange_apps", "sowia_night_exchange_events"):
        assert f"on public.{table} as restrictive for all to authenticated" in normalized
    assert normalized.count("using (public.sowia_has_professional_access())") == 5
    assert normalized.count("with check (public.sowia_has_professional_access())") == 6



def test_trusted_admins_can_read_night_exchange_moderation_queue_without_customer_premium():
    normalized = " ".join(MIGRATION.split())
    start = normalized.index('create policy "require premium for night exchange apps"')
    end = normalized.index('drop policy if exists "require premium for night exchange events"', start)
    policy = normalized[start:end]
    assert "auth.jwt() -> 'app_metadata' ->> 'role', '') = 'admin'" in policy
    assert "auth.jwt() -> 'app_metadata' ->> 'sowia_admin', '') = 'true'" in policy
    assert "with check (public.sowia_has_professional_access())" in policy
    assert "user_metadata" not in policy


def test_night_exchange_admin_exception_is_read_only():
    normalized = " ".join(MIGRATION.split())
    start = normalized.index('create policy "require premium for night exchange apps"')
    end = normalized.index('drop policy if exists "require premium for night exchange events"', start)
    policy = normalized[start:end]
    using_clause, check_clause = policy.split("with check", 1)
    assert "sowia_has_professional_access()" in using_clause
    assert "role', '') = 'admin'" in using_clause
    assert "sowia_admin', '') = 'true'" in using_clause
    assert "sowia_has_professional_access()" in check_clause
    assert "role', '') = 'admin'" not in check_clause
    assert "sowia_admin', '') = 'true'" not in check_clause

def test_migration_preserves_existing_rows_and_base_policies():
    assert "delete from " not in MIGRATION
    assert "truncate " not in MIGRATION
    assert "drop table " not in MIGRATION
    assert "create policy" in MIGRATION
