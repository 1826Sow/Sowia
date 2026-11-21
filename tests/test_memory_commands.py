import memory_commands


def test_parse_explicit_recall_command():
    assert memory_commands.parse_memory_command("Retrouve dans ma mémoire mes préférences") == {
        "action": "recall", "query": "mes préférences"
    }


def test_parse_explicit_forget_command():
    assert memory_commands.parse_memory_command("Oublie dans ma mémoire mon ancien projet") == {
        "action": "forget", "query": "mon ancien projet"
    }


def test_normal_chat_is_not_treated_as_memory_command():
    assert memory_commands.parse_memory_command("Je veux retrouver mon document") is None


def test_recall_matches_all_terms_without_case_or_accent_sensitivity():
    notes = [{"content": "Je préfère les explications en français."},
             {"content": "Projet professionnel à reprendre."}]
    assert memory_commands.find_memory_matches(notes, "FRANCAIS explications") == [notes[0]]


def test_forget_requires_query_to_identify_note():
    notes = [{"id": 1, "content": "Mon ancien projet SOW IA"},
             {"id": 2, "content": "Préférences de cuisine"}]
    assert memory_commands.find_exact_memory_matches(notes, "ancien projet") == [notes[0]]
    assert memory_commands.find_exact_memory_matches(notes, "projet") == [notes[0]]
    assert memory_commands.find_exact_memory_matches(notes, "inconnu") == []
