import pytest

from memory_retrieval import select_relevant_memories


def test_retrieval_prioritizes_notes_relevant_to_current_question():
    memories = [
        {"content": "Le projet SOW IA doit préserver les fonctionnalités opérationnelles."},
        {"content": "Préférence : réponses en français."},
        {"content": "SOW IA utilise NIGHT EXCHANGE pour les échanges entre applications."},
    ]
    selected = select_relevant_memories("Comment fonctionne NIGHT EXCHANGE dans SOW IA ?", memories)
    assert selected[0] == memories[2]["content"]
    assert memories[1]["content"] not in selected


def test_retrieval_falls_back_to_recent_notes_when_no_tokens_match():
    memories = [{"content": "Note récente"}, {"content": "Note ancienne"}]
    assert select_relevant_memories("question sans rapport", memories) == [
        "Note récente", "Note ancienne"
    ]


def test_unmatched_dictionary_fallback_returns_text_not_storage_records():
    memories = [{"id": 8, "content": "Souvenir récent", "created_at": "2026-11-22"}]
    assert select_relevant_memories("aucun mot commun", memories) == ["Souvenir récent"]


def test_metadata_only_records_are_not_injected_as_empty_memory():
    memories = [{"id": 1, "content": "", "title": "Titre sans contenu"}]
    assert select_relevant_memories("Titre", memories) == []


def test_retrieval_accepts_plain_strings_and_limits_results():
    assert select_relevant_memories("météo Paris", ["Météo de Paris", "Cuisine", "Projet"], limit=1) == [
        "Météo de Paris"
    ]


def test_retrieval_uses_note_title_and_tags_as_searchable_metadata_but_returns_content():
    note = {
        "content": "Procédure interne de sauvegarde.",
        "title": "Sécurité Supabase",
        "tags": ["authentification", "base de données"],
    }
    other = {"content": "Recette de cuisine"}
    assert select_relevant_memories("authentification Supabase", [other, note])[0] == note["content"]


def test_retrieval_handles_accented_and_unaccented_queries():
    note = "Prévisions météo et température à Évry."
    assert select_relevant_memories("previsions meteo Evry", [note]) == [note]


def test_retrieval_preserves_newest_first_order_for_equal_scores():
    notes = ["Projet SOW IA sauvegardé", "Projet SOW IA documenté"]
    assert select_relevant_memories("projet SOW IA", notes) == notes


def test_retrieval_returns_empty_for_empty_memory():
    assert select_relevant_memories("SOW IA", []) == []


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_retrieval_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="entier positif"):
        select_relevant_memories("question", ["note"], limit)
