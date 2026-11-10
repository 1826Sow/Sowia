"""Regression tests for the private SOWIA technical incident journal."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT / "supabase/migrations/20261110000200_sowia_technical_incidents.sql"
).read_text(encoding="utf-8").lower()


def _policy_block(policy_name):
    match = re.search(
        rf'create policy "{re.escape(policy_name.lower())}"(.*?);',
        MIGRATION,
        flags=re.DOTALL,
    )
    assert match, f"Missing policy: {policy_name}"
    return match.group(1)


def test_technical_incident_table_enforces_row_level_security():
    assert "alter table public.sowia_technical_incidents enable row level security" in MIGRATION


def test_incident_read_and_update_policies_require_admin_claims():
    for policy_name in ("sowia_incidents_admin_read", "sowia_incidents_admin_update"):
        block = _policy_block(policy_name)
        assert "to authenticated" in block
        assert "app_metadata" in block
        assert "sowia_admin" in block
        assert "role" in block
        assert " = 'true'" in block
        assert " = 'admin'" in block


def test_incident_journal_denies_anonymous_access_and_limits_server_grants():
    assert "revoke all on public.sowia_technical_incidents from anon" in MIGRATION
    assert (
        "grant select, update on public.sowia_technical_incidents to authenticated"
        in MIGRATION
    )
    assert (
        "grant select, insert, update on public.sowia_technical_incidents to service_role"
        in MIGRATION
    )
