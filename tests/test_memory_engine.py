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
    assert any("architecture mémoire" in item for item in result)


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


def test_empty_inputs_are_safe():
    assert select_relevant_memories(None) == []
    assert select_relevant_memories(["   "], "mémoire") == []
