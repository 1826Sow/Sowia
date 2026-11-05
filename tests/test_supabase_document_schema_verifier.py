from pathlib import Path


def _verifier():
    return (Path(__file__).resolve().parents[1] / "supabase" / "verify_security.sql").read_text(
        encoding="utf-8"
    )


def test_verifier_checks_all_required_document_content_columns():
    sql = _verifier()
    for column in ("title", "filename", "extracted_text", "text_length", "deleted_at"):
        assert f"('sowia_documents', '{column}')" in sql


def test_verifier_checks_document_content_and_metadata_constraints():
    sql = _verifier()
    assert "Contrainte de taille du texte extrait" in sql
    assert "Contrainte de catégorie des documents" in sql
    assert "Contrainte de longueur du dossier" in sql
    assert "pg_get_constraintdef" in sql


def test_verifier_checks_owner_scoped_authenticated_policies():
    sql = _verifier()
    assert "'authenticated'::name = any(pol.roles)" in sql
    assert "auth.uid%" in sql
    assert "user_id%" in sql


def test_verifier_remains_read_only():
    sql = _verifier().lower()
    forbidden = (
        "insert into ",
        "update public.",
        "delete from ",
        "alter table ",
        "drop table ",
        "create policy ",
        "create index ",
    )
    assert not any(statement in sql for statement in forbidden)
