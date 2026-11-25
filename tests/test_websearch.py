import pytest

import websearch


def test_search_web_uses_free_public_search_when_tavily_key_is_missing(monkeypatch):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "")
    monkeypatch.setattr(websearch, "_free_search", lambda query, count: [
        {"title": "Exemple", "url": "https://example.test", "content": "Résumé"}
    ])
    assert websearch.search_web("  actualité  ") == [
        {"title": "Exemple", "url": "https://example.test", "content": "Résumé"}
    ]


@pytest.mark.parametrize("query", ["", "   ", None])
def test_search_web_rejects_empty_query(monkeypatch, query):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "test-key")

    with pytest.raises(ValueError, match="Saisissez une recherche"):
        websearch.search_web(query)


def test_search_web_rejects_query_longer_than_500_characters(monkeypatch):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "test-key")

    with pytest.raises(ValueError, match="500 caractères"):
        websearch.search_web("x" * 501)


@pytest.mark.parametrize("max_results", [0, 11, 1.5, True])
def test_search_web_rejects_invalid_result_count(monkeypatch, max_results):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "test-key")

    with pytest.raises(ValueError, match="résultats"):
        websearch.search_web("actualité", max_results=max_results)


def test_search_web_sends_trimmed_query_and_returns_results(monkeypatch):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "test-key")

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"title": "Exemple"}]}

    captured = {}

    def fake_post(url, json, timeout):
        captured.update(url=url, json=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(websearch.requests, "post", fake_post)

    assert websearch.search_web("  actualité  ") == [{"title": "Exemple"}]
    assert captured["json"]["query"] == "actualité"
    assert captured["json"]["max_results"] == 5
    assert captured["timeout"] == 25


def test_search_web_hides_transport_error_details(monkeypatch):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "test-key")

    def fail_post(*args, **kwargs):
        raise websearch.requests.ConnectionError("private transport detail")

    monkeypatch.setattr(websearch.requests, "post", fail_post)

    with pytest.raises(RuntimeError, match="momentanément indisponible") as error:
        websearch.search_web("actualité")
    assert "private transport detail" not in str(error.value)


@pytest.mark.parametrize("query", [
    "Quelles sont les dernières actualités de l'IA ?",
    "Quel est le prix actuel de ce service ?",
    "Quelle est la météo aujourd'hui ?",
    "Find the latest version available right now",
    "Donne-moi les résultats en direct",
    "Cherche en ligne les dernières informations",
])
def test_should_search_web_for_fresh_information(query):
    assert websearch.should_search_web(query) is True


@pytest.mark.parametrize("query", [
    "Explique-moi le fonctionnement d'un réseau neuronal",
    "Aide-moi à rédiger une lettre professionnelle",
    "Comment fonctionne une base de données relationnelle ?",
])
def test_should_not_search_web_for_stable_or_writing_requests(query):
    assert websearch.should_search_web(query) is False

@pytest.mark.parametrize("query", [
    "SOW IA, cherche sur Internet les sources officielles",
    "Peux-tu trouver des liens officiels sur le web ?",
    "Consulte des sources en ligne pour cette information",
    "Qui est le président actuel en 2026 ?",
    "Est-ce que ce service est toujours disponible ?",
    "Je veux la navigation Internet sur ce sujet",
])
def test_should_search_web_for_explicit_browsing_and_current_facts(query):
    assert websearch.should_search_web(query) is True


@pytest.mark.parametrize("query", [
    "Explique simplement ce qu'est une API",
    "Rédige un message de remerciement",
    "Aide-moi à organiser mon projet",
])
def test_should_keep_simple_requests_on_the_fast_ai_path(query):
    assert websearch.should_search_web(query) is False
