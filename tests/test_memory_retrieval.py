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


def test_retrieval_accepts_plain_strings_and_limits_results():
    assert select_relevant_memories("météo Paris", ["Météo de Paris", "Cuisine", "Projet"], limit=1) == [
        "Météo de Paris"
    ]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_retrieval_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="entier positif"):
        select_relevant_memories("question", ["note"], limit)
