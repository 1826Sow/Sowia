from pathlib import Path
import re


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20261121190000_night_exchange_domain_challenges.sql"
)


def test_domain_challenge_storage_is_non_exposed_and_server_only():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create schema if not exists sowia_private" in sql
    assert "revoke all on schema sowia_private from public, anon, authenticated" in sql
    assert "grant usage on schema sowia_private to service_role" in sql
    assert "alter table sowia_private.nex_domain_challenges enable row level security" in sql
    assert "alter table sowia_private.nex_domain_verification_audit enable row level security" in sql
    assert "revoke all on table sowia_private.nex_domain_challenges" in sql
    assert "revoke all on table sowia_private.nex_domain_verification_audit" in sql


def test_only_token_digest_is_persisted_and_challenge_has_expiry():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert re.search(r"token_hash\\s+bytea\\s+not null\\s+check\\s*\\(octet_length\\(token_hash\\)\\s*=\\s*32\\)", sql)
    assert "token text" not in sql
    assert "expires_at timestamptz not null" in sql
    assert "check (expires_at > issued_at)" in sql
    assert "p_ttl_seconds < 300 or p_ttl_seconds > 172800" in sql


def test_consumption_is_atomic_owner_domain_hash_bound_and_audited():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    consume = sql.split("create or replace function sowia_private.consume_nex_domain_challenge", 1)[1]
    assert "update sowia_private.nex_domain_challenges" in consume
    assert "c.owner_id = p_owner_id" in consume
    assert "c.domain = lower(btrim(p_domain))" in consume
    assert "c.token_hash = p_token_hash" in consume
    assert "c.consumed_at is null" in consume
    assert "c.expires_at > v_consumed_at" in consume
    assert "proof_consumed" in consume


def test_rpc_wrappers_are_invoker_and_service_role_only():
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    assert "create or replace function public.sowia_issue_nex_domain_challenge" in sql
    assert "create or replace function public.sowia_consume_nex_domain_challenge" in sql
    assert len(re.findall(r"^\\s*security invoker\\s*$", sql, re.MULTILINE)) == 2
    assert "grant execute on function public.sowia_issue_nex_domain_challenge" in sql
    assert "grant execute on function public.sowia_consume_nex_domain_challenge" in sql
    assert "to service_role" in sql
    assert "grant execute on function public.sowia_issue_nex_domain_challenge(uuid, text, bytea, integer) to authenticated" not in sql
}
