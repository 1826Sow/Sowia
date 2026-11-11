"""Disposable-PostgreSQL integration checks for the FINAL TEC audit vault.

Run only against a fresh throwaway PostgreSQL database:
FINAL_TEC_TEST_DATABASE_URL=postgresql://... pytest -q tests/integration/test_final_tec_audit_vault_postgres.py

This is not a live Supabase Auth/RLS integration test. It emulates the small
Supabase role/auth.role() surface needed to exercise the SQL proposal.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
DATABASE_URL = os.getenv("FINAL_TEC_TEST_DATABASE_URL")
if not DATABASE_URL:
    pytest.skip("FINAL_TEC_TEST_DATABASE_URL not configured; disposable DB only", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = ROOT / "supabase" / "proposals" / "final_tec_audit_vault.sql"
ACTOR = UUID("00000000-0000-0000-0000-000000000123")


@pytest.fixture(scope="module", autouse=True)
def install_proposal():
    """Install into a fresh ephemeral DB with minimal Supabase-compatible roles."""
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("create schema auth")
        conn.execute("create schema extensions")
        conn.execute("create role anon nologin")
        conn.execute("create role authenticated nologin")
        conn.execute("create role service_role nologin bypassrls")
        conn.execute("""
            create function auth.role() returns text
            language sql stable
            as $$ select nullif(current_setting('request.jwt.claim.role', true), '') $$
        """)
        conn.execute("""
            create table public.final_tec_investor_access (
                user_id uuid not null,
                project_key text not null,
                role text not null,
                status text not null,
                starts_at timestamptz not null,
                expires_at timestamptz
            )
        """)
        conn.execute(SQL_PATH.read_text(encoding="utf-8"))
        conn.execute("""
            insert into public.final_tec_investor_access
                (user_id, project_key, role, status, starts_at, expires_at)
            values (%s, 'final-tec', 'final_tec_investor_viewer', 'active', now() - interval '1 minute', null)
        """, (ACTOR,))
    yield


def _append(index: int) -> tuple[int, str, str]:
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("set role service_role")
        conn.execute("select set_config('request.jwt.claim.role', 'service_role', false)")
        row = conn.execute("""
            select sequence_id, event_hash, previous_hash
            from public.final_tec_append_audit_event(
                %s, 'final_tec_investor_viewer', 'investor_dashboard_viewed',
                'dashboard', %s, 'allowed', 'dashboard_view'
            )
        """, (ACTOR, f"concurrent-{index}")).fetchone()
        assert row is not None
        return int(row[0]), str(row[1]), str(row[2])


def test_concurrent_appends_form_one_ordered_hash_chain():
    count = 32
    with ThreadPoolExecutor(max_workers=8) as pool:
        inserted = list(pool.map(_append, range(count)))

    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("""
            select sequence_id, previous_hash, event_hash
            from final_tec_private.audit_events
            order by sequence_id
        """).fetchall()

    assert len(rows) == count
    assert len({row[0] for row in rows}) == count
    assert rows[0][1] == "0" * 64
    for previous, current in zip(rows, rows[1:]):
        assert current[1] == previous[2]
    # Every RPC receipt corresponds to one committed row.
    assert {row[0] for row in inserted} == {row[0] for row in rows}


@pytest.mark.parametrize("db_role", ["anon", "authenticated"])
def test_client_roles_cannot_read_private_audit_table(db_role: str):
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(f"set role {db_role}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from final_tec_private.audit_events").fetchall()
        conn.rollback()


def test_viewer_assignment_cannot_append_an_admin_action():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("set role service_role")
        conn.execute("select set_config('request.jwt.claim.role', 'service_role', false)")
        with pytest.raises(psycopg.errors.RaiseException, match="action_not_permitted_for_role"):
            conn.execute("""
                select * from public.final_tec_append_audit_event(
                    %s, 'final_tec_investor_viewer', 'access_granted',
                    'access', 'unauthorized', 'allowed', 'test_denied'
                )
            """, (ACTOR,))


def test_expired_or_missing_assignment_is_rejected():
    other_actor = uuid4()
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("set role service_role")
        conn.execute("select set_config('request.jwt.claim.role', 'service_role', false)")
        with pytest.raises(psycopg.errors.RaiseException, match="active_final_tec_assignment_required"):
            conn.execute("""
                select * from public.final_tec_append_audit_event(
                    %s, 'final_tec_investor_viewer', 'investor_dashboard_viewed',
                    'dashboard', 'unassigned', 'allowed', 'dashboard_view'
                )
            """, (other_actor,))


def test_service_role_cannot_mutate_existing_audit_events():
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        conn.execute("set role service_role")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("update final_tec_private.audit_events set reason_code='tampered'")
