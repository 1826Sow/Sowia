from pathlib import Path


def test_read_only_supabase_verifier_checks_authenticated_policy_role():
    sql = (Path(__file__).resolve().parents[1] / "supabase" / "verify_security.sql").read_text(
        encoding="utf-8"
    )
    assert "'authenticated'::name = any(pol.roles)" in sql


def test_read_only_supabase_verifier_checks_recycle_bin_index():
    sql = (Path(__file__).resolve().parents[1] / "supabase" / "verify_security.sql").read_text(
        encoding="utf-8"
    )
    assert "sowia_documents_user_deleted_idx" in sql
    assert "deleted_at" in sql
    assert "pg_indexes" in sql


def test_read_only_supabase_verifier_does_not_modify_schema_or_data():
    sql = (Path(__file__).resolve().parents[1] / "supabase" / "verify_security.sql").read_text(
        encoding="utf-8"
    ).lower()
    forbidden = ("insert into ", "update public.", "delete from ", "alter table ", "drop table ", "create policy ")
    assert not any(statement in sql for statement in forbidden)
