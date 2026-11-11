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
        "sowia_business_club_profiles",
        "sowia_business_club_requests",
        "sowia_business_club_meetings",
        "sowia_night_exchange_apps",
        "sowia_night_exchange_events",
    )
    for table in tables:
        assert f"on public.{table} as restrictive for all to authenticated" in normalized
        assert f"drop policy if exists" in normalized
    assert normalized.count("public.sowia_has_professional_access()") >= 7


def test_personal_rows_remain_available_without_premium_where_supported():
    normalized = " ".join(MIGRATION.split())
    assert normalized.count("workspace_id = 'personal' or public.sowia_has_professional_access()") == 4


def test_business_club_and_night_exchange_remain_professional_only():
    normalized = " ".join(MIGRATION.split())
    for table in ("sowia_business_club_profiles", "sowia_business_club_requests", "sowia_business_club_meetings", "sowia_night_exchange_apps", "sowia_night_exchange_events"):
        assert f"on public.{table} as restrictive for all to authenticated" in normalized
    assert normalized.count("using (public.sowia_has_professional_access())") == 5
    assert normalized.count("with check (public.sowia_has_professional_access())") == 5


def test_migration_preserves_existing_rows_and_base_policies():
    assert "delete from " not in MIGRATION
    assert "truncate " not in MIGRATION
    assert "drop table " not in MIGRATION
    assert "create policy" in MIGRATION
