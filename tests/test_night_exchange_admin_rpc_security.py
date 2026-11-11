"""Regression guards for the NIGHT EXCHANGE moderation boundary."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase_night_exchange_registry.sql").read_text(encoding="utf-8").lower()


def test_admin_review_rpc_is_security_definer_with_empty_search_path():
    match = re.search(
        r"create or replace function public\.sowia_admin_review_nex_app\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match, "Moderation RPC must exist"
    declaration = SQL[match.start():match.start(1)]
    body = match.group(2)
    assert "security definer" in declaration
    assert "set search_path = ''" in declaration
    assert "public.sowia_night_exchange_apps" in body


def test_moderation_rpc_uses_only_trusted_admin_claims_and_valid_statuses():
    match = re.search(
        r"create or replace function public\.sowia_admin_review_nex_app\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match
    body = match.group(2)
    assert "auth.jwt() -> 'app_metadata' ->> 'role'" in body
    assert "auth.jwt() -> 'app_metadata' ->> 'sowia_admin'" in body
    assert "user_metadata" not in body
    assert "p_status not in ('approved', 'rejected', 'suspended')" in body
    assert "p_moderation_note is null" in body
    assert "char_length(p_moderation_note) > 1000" in body


def test_moderation_rpc_execution_is_allowlisted_for_authenticated_users():
    assert (
        "revoke all on function public.sowia_admin_review_nex_app(uuid, text, text) from public"
    ) in SQL
    assert (
        "grant execute on function public.sowia_admin_review_nex_app(uuid, text, text) to authenticated"
    ) in SQL


def test_partner_edits_cannot_self_approve_or_retain_moderation_metadata():
    match = re.search(
        r"create or replace function public\.sowia_nex_guard_app_listing\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match
    body = match.group(2)
    assert "new.status := 'pending'" in body
    assert "new.verified_at := null" in body
    assert "new.moderation_note := null" in body
    assert "auth.jwt() -> 'app_metadata'" in body


def test_clients_can_write_only_partner_editable_columns():
    assert (
        "revoke insert, update on public.sowia_night_exchange_apps from authenticated"
    ) in SQL
    assert (
        "grant insert ( user_id, workspace_id, app_name, country, timezone, categories,"
    ) in SQL
    assert (
        "grant update ( workspace_id, app_name, country, timezone, categories,"
    ) in SQL
    assert "grant select, delete on public.sowia_night_exchange_apps to authenticated" in SQL
    assert "grant select, insert, update, delete on public.sowia_night_exchange_apps to authenticated" not in SQL
