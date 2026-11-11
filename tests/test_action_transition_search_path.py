"""Regression guards for SECURITY DEFINER action-transition hardening."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase_global_action_governance.sql").read_text(encoding="utf-8").lower()


def test_action_transition_security_definer_uses_empty_search_path():
    match = re.search(
        r"create or replace function public\.sowia_action_transition\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match, "Action transition function must exist with a valid dollar-quoted body"
    declaration = SQL[match.start():match.start(1)]
    body = match.group(2)
    assert "security definer" in declaration
    assert "set search_path = ''" in declaration
    assert "auth.uid()" in body
    assert "public.sowia_global_action_plans" in body
    assert "public.sowia_global_action_audit" in body
    assert "set search_path = public" not in declaration


def test_action_transition_execution_is_not_granted_to_unauthenticated_roles():
    assert (
        "revoke all on function public.sowia_action_transition(uuid,text,text) "
        "from public, anon"
    ) in SQL
    assert (
        "grant execute on function public.sowia_action_transition(uuid,text,text) "
        "to authenticated"
    ) in SQL
