import pytest

import websearch


def test_search_web_explains_streamlit_secret_when_key_is_missing(monkeypatch):
    monkeypatch.setattr(websearch, "TAVILY_API_KEY", "")

    with pytest.raises(RuntimeError, match="secrets Streamlit"):
        websearch.search_web("actualité")


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
