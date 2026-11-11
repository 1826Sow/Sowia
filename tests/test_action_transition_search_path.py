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



def test_action_transition_uses_one_valid_plpgsql_declare_section():
    match = re.search(
        r"create or replace function public\.sowia_action_transition\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match, "Action transition function must exist"
    body = match.group(2)
    assert re.search(
        r"\bdeclare\s+p public\.sowia_global_action_plans%rowtype;\s+actor uuid := auth\.uid\(\);\s+begin\b",
        body,
    ), "PL/pgSQL variables must share one DECLARE section"
    assert not re.search(r"\bdeclare\s+p[^;]+;\s*declare\b", body)


def test_action_tables_revoke_old_authenticated_grants_before_allowlisting():
    revoke = (
        "revoke all on public.sowia_global_action_plans, "
        "public.sowia_global_action_audit from anon, public, authenticated"
    )
    assert revoke in SQL
    assert (
        "grant select, insert on public.sowia_global_action_plans to authenticated"
    ) in SQL
    assert "grant select on public.sowia_global_action_audit to authenticated" in SQL
    assert "grant update on public.sowia_global_action_plans to authenticated" not in SQL
    assert "grant delete on public.sowia_global_action_plans to authenticated" not in SQL
    assert "grant insert on public.sowia_global_action_audit to authenticated" not in SQL


def test_action_tables_keep_rls_and_scoped_read_policies():
    assert "alter table public.sowia_global_action_plans enable row level security" in SQL
    assert "alter table public.sowia_global_action_audit enable row level security" in SQL
    assert (
        "for select to authenticated using (creator_id = auth.uid() or approver_id = auth.uid())"
    ) in SQL
    assert (
        "for insert to authenticated with check (creator_id = auth.uid() and status = 'draft' and approver_id <> creator_id)"
    ) in SQL
    assert "p.creator_id = auth.uid() or p.approver_id = auth.uid()" in SQL



def test_action_transition_enforces_two_party_approval_and_audit_trail():
    match = re.search(
        r"create or replace function public\.sowia_action_transition\([\s\S]*?as (\$[a-z_]*\$)([\s\S]*?)\1;",
        SQL,
    )
    assert match
    body = match.group(2)
    assert "for update" in body
    assert "p.creator_id = actor" in body
    assert "p.approver_id = actor and p.creator_id <> actor" in body
    assert "p_next_status in ('approved','rejected')" in body
    assert "insert into public.sowia_global_action_audit" in body
    assert "values(p.id,actor,p.status,p_next_status,coalesce(p_note,''))" in body



def test_action_plan_insert_privileges_exclude_server_owned_workflow_fields():
    revoke = (
        "revoke all on public.sowia_global_action_plans, "
        "public.sowia_global_action_audit from anon, public, authenticated"
    )
    assert revoke in SQL
    assert "grant select on public.sowia_global_action_plans to authenticated" in SQL
    assert (
        "grant insert (\n    creator_id, title, objective, country, owner_label, budget_cap, currency,\n"
        "    due_date, success_metric, stop_condition, approver_id\n"
        ") on public.sowia_global_action_plans to authenticated"
    ) in SQL
    assert "grant select, insert on public.sowia_global_action_plans to authenticated" not in SQL
