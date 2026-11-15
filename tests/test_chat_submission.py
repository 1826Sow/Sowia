from chat_submission import normalize_chat_prompt


def test_normalize_chat_prompt_trims_non_empty_text():
    assert normalize_chat_prompt("  Bonjour SOW IA  ") == "Bonjour SOW IA"


def test_normalize_chat_prompt_rejects_empty_or_whitespace():
    assert normalize_chat_prompt("") is None
    assert normalize_chat_prompt("   \n  ") is None


def test_normalize_chat_prompt_rejects_non_text_values():
    assert normalize_chat_prompt(None) is None
    assert normalize_chat_prompt(123) is None
