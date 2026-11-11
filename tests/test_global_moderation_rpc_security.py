"""Static security regression tests for administrator moderation RPCs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase_global_moderation.sql").read_text(encoding="utf-8").lower()


def _function_body(signature):
    start = SQL.index(signature)
    end = SQL.index("$$;", SQL.index("as $$", start)) + 3
    return SQL[start:end]


def test_moderation_rpc_functions_use_empty_search_path_and_server_admin_claim():
    signatures = (
        "create or replace function public.sowia_admin_update_global_trust_report(",
        "create or replace function public.sowia_admin_update_global_profile_status(",
    )
    for signature in signatures:
        body = _function_body(signature)
        assert "security definer set search_path = ''" in body
        assert "auth.uid()" in body
        assert "auth.jwt() -> 'app_metadata'" in body
        assert "user_metadata" not in body
        assert "raise exception 'sowia administrator access required'" in body


def test_moderation_rpc_execution_is_revoked_from_public_and_anon():
    assert (
        "revoke all on function public.sowia_admin_update_global_trust_report(uuid,text,text) "
        "from public,anon"
    ) in SQL
    assert (
        "revoke all on function public.sowia_admin_update_global_profile_status(uuid,text,text,text) "
        "from public,anon"
    ) in SQL
    assert (
        "grant execute on function public.sowia_admin_update_global_trust_report(uuid,text,text) "
        "to authenticated"
    ) in SQL
    assert (
        "grant execute on function public.sowia_admin_update_global_profile_status(uuid,text,text,text) "
        "to authenticated"
    ) in SQL


def test_moderation_audit_has_no_direct_client_write_grants():
    assert (
        "revoke all on public.sowia_global_moderation_audit from public, anon, authenticated"
    ) in SQL
    assert "grant select on public.sowia_global_moderation_audit to authenticated" in SQL
    assert "grant insert on public.sowia_global_moderation_audit to authenticated" not in SQL
    assert "grant update on public.sowia_global_moderation_audit to authenticated" not in SQL
    assert "grant delete on public.sowia_global_moderation_audit to authenticated" not in SQL
