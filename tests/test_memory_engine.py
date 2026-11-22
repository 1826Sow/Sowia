from memory_engine import (
    MAX_MEMORY_CONTEXT_CHARS,
    infer_memory_category,
    memory_context_summary,
    select_relevant_memories,
)


def test_memory_context_prioritizes_relevant_project_knowledge():
    memories = [
        {"content": "Préférence générale pour les réponses courtes.", "category": "preference", "importance": 2},
        {"content": "SOW IA utilise Supabase RLS pour isoler les données des utilisateurs.", "category": "technical", "importance": 5},
        {"content": "Recette de tarte aux pommes.", "category": "general", "importance": 3},
    ]
    result = select_relevant_memories(memories, "Comment fonctionne Supabase RLS ?")
    assert "Supabase RLS" in result
    assert "tarte aux pommes" not in result


def test_memory_context_is_bounded_without_truncating_archive_storage():
    memories = [{"content": "x" * 20000, "importance": 5} for _ in range(4)]
    result = select_relevant_memories(memories, "x", max_chars=7000)
    assert len(result) <= 7000
    assert "x" in result


def test_memory_context_deduplicates_and_keeps_high_importance():
    memories = [
        {"content": "Décision technique validée pour le projet.", "importance": 5},
        {"content": "Décision technique validée pour le projet.", "importance": 5},
        {"content": "Note secondaire.", "importance": 1},
    ]
    result = select_relevant_memories(memories, "décision technique")
    assert result.count("Décision technique validée") == 1


def test_infer_memory_category_for_project_and_technical_notes():
    assert infer_memory_category("Architecture Supabase et API GitHub") == "technical"
    assert infer_memory_category("Roadmap du projet et livrables") == "project"
    assert infer_memory_category("Je préfère les explications étape par étape") == "preference"


def test_memory_context_summary_counts_categories_without_content():
    result = memory_context_summary([
        {"content": "Projet A", "category": "project"},
        {"content": "Code", "category": "technical"},
        {"content": " "},
    ])
    assert result == {"count": 2, "by_category": {"project": 1, "technical": 1}}


def test_default_context_budget_is_expanded():
    assert MAX_MEMORY_CONTEXT_CHARS >= 30000
