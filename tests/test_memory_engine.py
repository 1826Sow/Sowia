import pytest

from memory_engine import build_agent_memory_context, select_relevant_memories


def test_retrieval_prioritises_relevant_memory_and_keeps_project_context():
    memories = [
        "Préférence : réponses courtes.",
        "Projet actif : SOW IA. Statut : En cours. Architecture mémoire.",
        "Le projet SOWKEYS concerne un ebook de cuisine.",
    ]
    result = select_relevant_memories(memories, "architecture mémoire SOW IA")
    assert result[0].startswith("Projet actif :")
    assert any("architecture mémoire" in item.casefold() for item in result)


def test_generic_query_preserves_source_order_and_removes_duplicates():
    memories = ["Premier fait", "Deuxième fait", "Premier fait"]
    assert select_relevant_memories(memories) == ["Premier fait", "Deuxième fait"]


def test_context_is_bounded_by_item_and_character_limits():
    result = select_relevant_memories(["a" * 9000, "b" * 9000], max_items=1, max_chars=500)
    assert len(result) == 1
    assert len(result[0]) == 500


def test_agent_entry_point_uses_same_scoped_retrieval():
    records = [{"content": "Le développeur travaille sur la mémoire SOW IA."}]
    result = build_agent_memory_context(records, "développeur mémoire")
    assert result == ["Le développeur travaille sur la mémoire SOW IA."]


def test_metadata_title_and_tags_make_memory_discoverable():
    memories = [
        {"content": "La procédure explique les accès.", "title": "Sécurité Supabase",
         "tags": ["RLS", "authentification"]},
        {"content": "Recette de cuisine."},
    ]
    result = select_relevant_memories(memories, "authentification Supabase")
    assert result == ["La procédure explique les accès."]


def test_metadata_is_used_for_search_but_not_injected_into_prompt():
    note = {
        "content": "La note décrit les contrôles de permission.",
        "category": "Développement agents IA",
        "document_name": "Guide API SQL",
    }
    result = build_agent_memory_context([note], "Guide API SQL")
    assert result == [note["content"]]
    assert "Guide API SQL" not in result[0]


def test_short_technical_terms_and_accent_variants_are_searchable():
    note = {"content": "Le système gère les interfaces et documents.", "tags": ["API", "PDF", "Évry"]}
    assert select_relevant_memories([note], "api pdf Evry") == [note["content"]]


def test_body_match_ranks_above_metadata_only_match():
    memories = [
        {"content": "Le document concerne les réglages du compte.", "title": "API"},
        {"content": "L'API expose les outils du développeur."},
    ]
    result = select_relevant_memories(memories, "API développeur")
    assert result[0] == memories[1]["content"]


def test_project_context_remains_pinned_even_when_metadata_matches_other_note():
    memories = [
        {"content": "Une note sur les rapports.", "tags": ["finance"]},
        "Projet actif : SOW IA. Architecture des agents.",
    ]
    result = select_relevant_memories(memories, "finance")
    assert result[0].startswith("Projet actif :")


def test_generic_agent_context_preserves_source_order():
    records = [
        {"content": "Premier fait", "title": "Guide"},
        {"content": "Deuxième fait", "tags": ["technique"]},
    ]
    assert build_agent_memory_context(records) == ["Premier fait", "Deuxième fait"]


def test_empty_inputs_are_safe():
    assert select_relevant_memories(None) == []
    assert select_relevant_memories(["   "], "mémoire") == []


def test_retrieval_does_not_mutate_authorized_memory_records():
    record = {"content": "Mémoire SOW IA.", "title": "Architecture"}
    original = dict(record)
    build_agent_memory_context([record], "architecture")
    assert record == original
