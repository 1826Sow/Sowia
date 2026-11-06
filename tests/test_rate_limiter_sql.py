"""Static guardrails for the candidate shared rate-limit SQL migration."""
from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "202611060001_shared_rate_limits.sql"
)


def migration_sql():
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_rate_limit_table_is_per_user_and_per_bucket_with_rls():
    sql = migration_sql()
    assert "user_id uuid not null references auth.users(id)" in sql
    assert "primary key (user_id, bucket_key)" in sql
    assert "enable row level security" in sql
    assert "revoke all on table public.sowia_rate_limits from public, anon, authenticated" in sql


def test_rate_limit_rpc_is_security_definer_with_fixed_search_path():
    sql = migration_sql()
    assert "security definer" in sql
    assert "set search_path = pg_catalog" in sql
    assert "auth.uid()" in sql
    assert "if v_user_id is null" in sql


def test_rate_limit_rpc_owns_allowlist_and_fixed_quotas():
    sql = migration_sql()
    for bucket in (
        "assistant", "pdf_question", "advanced_pdf", "batch_pdf",
        "web_search", "document_upload", "document_download", "document_delete",
    ):
        assert f"when '{bucket}' then" in sql
    assert "p_bucket_key" in sql
    assert "invalid rate limit bucket" in sql


def test_rate_limit_rpc_uses_atomic_upsert_and_returns_server_decision():
    sql = migration_sql()
    assert "on conflict (user_id, bucket_key) do update" in sql
    assert "returning current_limit.window_started_at, current_limit.request_count" in sql
    assert "allowed := v_count <= v_limit" in sql
    assert "remaining := greatest(v_limit - v_count, 0)" in sql


def test_rate_limit_rpc_is_not_executable_by_public_or_anonymous():
    sql = migration_sql()
    assert "revoke all on function public.sowia_consume_rate_limit(text) from public, anon" in sql
    assert "grant execute on function public.sowia_consume_rate_limit(text) to authenticated" in sql
