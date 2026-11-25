import memory_commands as commands


def test_parse_explicit_memory_recall_in_french():
    assert commands.parse_memory_command("Retrouve dans ma mémoire mes préférences") == {
        "action": "recall", "query": "mes préférences"
    }


def test_parse_explicit_memory_forget_in_french():
    assert commands.parse_memory_command("Supprime de ma mémoire mon ancien projet") == {
        "action": "forget", "query": "mon ancien projet"
    }


def test_parse_explicit_memory_recall_in_english():
    assert commands.parse_memory_command("Find in my memory SOW IA") == {
        "action": "recall", "query": "SOW IA"
    }


def test_ordinary_conversation_is_not_a_memory_command():
    assert commands.parse_memory_command("Oublie de répondre à ma question") is None
    assert commands.parse_memory_command("Explique-moi la mémoire des agents IA") is None


def test_empty_or_ambiguous_command_is_not_executed():
    assert commands.parse_memory_command("Retrouve dans ma mémoire") is None
    assert commands.parse_memory_command("Supprime de ma mémoire") is None


def test_recall_matches_all_terms_and_preserves_order():
    records = [
        {"id": "1", "content": "SOW IA utilise une mémoire persistante."},
        {"id": "2", "content": "SOW IA possède une recherche Web."},
        {"id": "3", "content": "Une autre application."},
    ]
    assert commands.find_memory_matches(records, "SOW IA mémoire") == [records[0]]


def test_forget_requires_full_phrase_and_does_not_delete_ambiguous_records():
    records = [
        {"id": "1", "content": "Ancien projet SOW IA abandonné."},
        {"id": "2", "content": "Projet SOW IA actuel."},
    ]
    assert commands.find_exact_memory_matches(records, "projet SOW IA") == records
    assert commands.find_exact_memory_matches(records, "ancien projet SOW IA") == [records[0]]


def test_memory_helpers_ignore_malformed_records():
    assert commands.find_memory_matches([None, "not a record"], "memory") == []
