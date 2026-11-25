"""Tests for automatic live-information detection."""
from live_intelligence import should_search_web


def test_current_information_triggers_search():
    assert should_search_web("Quelles sont les dernières nouvelles de l'IA ?")
    assert should_search_web("Quel est le prix actuel du bitcoin ?")
    assert should_search_web("What happened today in AI?")


def test_general_reasoning_does_not_trigger_search():
    assert not should_search_web("Explique-moi les réseaux de neurones.")
    assert not should_search_web("Aide-moi à structurer mon projet.")
    assert not should_search_web("Que sais-tu de ma mémoire personnelle ?")


def test_empty_prompt_does_not_trigger_search():
    assert not should_search_web("")
