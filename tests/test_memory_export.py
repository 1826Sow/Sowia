from memory_export import format_memory_export


def test_memory_export_includes_only_supplied_notes_and_workspace():
    result = format_memory_export(
        [
            {"content": "Préférence français", "created_at": "2026-11-09"},
            {"content": "Projet SOW IA"},
        ],
        "personnel",
    )

    assert "Espace : Personnel" in result
    assert "Nombre de notes : 2" in result
    assert "Préférence français" in result
    assert "Projet SOW IA" in result
    assert "Date : 2026-11-09" in result


def test_memory_export_handles_empty_notes():
    result = format_memory_export([], "professionnel")

    assert "Espace : Professionnel" in result
    assert "Nombre de notes : 0" in result
    assert result.endswith("\n")


def test_memory_export_skips_blank_note_content():
    result = format_memory_export(
        [{"content": "   "}, {"content": "Note utile"}],
        "personnel",
    )

    assert "Note utile" in result
    assert "\nNote 2\n" not in result


def test_memory_export_preserves_memory_metadata():
    result = format_memory_export(
        [{
            "content": "Architecture SOW IA",
            "category": "technical",
            "importance": 5,
            "source": "project",
            "tags": ["SOW IA", "Supabase"],
            "project_id": 42,
        }],
        "professionnel",
    )
    assert "Catégorie : technical" in result
    assert "Priorité : 5/5" in result
    assert "Source : project" in result
    assert "Tags : SOW IA, Supabase" in result
    assert "Projet ID : 42" in result
