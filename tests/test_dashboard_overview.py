from datetime import datetime, timezone

import dashboard_overview


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self):
        self.metrics = []
        self.buttons = []

    def markdown(self, *args, **kwargs):
        pass

    def caption(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def metric(self, *args, **kwargs):
        self.metrics.append(args)

    def button(self, *args, **kwargs):
        self.buttons.append(args)

    def columns(self, count):
        return [_Context() for _ in range(count)]

    def container(self, **kwargs):
        return _Context()


def test_format_updated_handles_utc_timestamp():
    result = dashboard_overview._format_updated(
        datetime(2026, 11, 22, 12, 30, tzinfo=timezone.utc).isoformat()
    )
    assert result != "Date indisponible"
    assert "22/11/2026" in result


def test_format_updated_handles_missing_or_invalid_values():
    assert dashboard_overview._format_updated(None) == "Date indisponible"
    assert dashboard_overview._format_updated("not-a-date") == "Date indisponible"


def test_render_reads_only_the_active_workspace(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(dashboard_overview, "st", fake_st)
    calls = []

    def list_projects(client, user, workspace_id, limit):
        calls.append(("projects", client, user, workspace_id, limit))
        return [{"id": 1, "title": "Projet de test", "status": "En cours"}]

    def list_conversations(client, user, workspace_id, limit):
        calls.append(("conversations", client, user, workspace_id, limit))
        return [{"session_id": "session-1", "title": "Échange de test"}]

    monkeypatch.setattr(dashboard_overview.project_registry, "list_projects", list_projects)
    monkeypatch.setattr(dashboard_overview.cloud_storage, "list_conversations", list_conversations)

    client = object()
    user = object()
    dashboard_overview.render(
        client, user, "professional", True, True, navigate=lambda page: None
    )

    assert [(call[0], call[3]) for call in calls] == [
        ("projects", "professional"),
        ("conversations", "professional"),
    ]
    assert all(call[1] is client and call[2] is user for call in calls)
    assert len(fake_st.buttons) == 2


def test_render_does_not_read_professional_data_without_premium(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Professional data must not be read without Premium access.")

    monkeypatch.setattr(dashboard_overview.project_registry, "list_projects", forbidden)
    monkeypatch.setattr(dashboard_overview.cloud_storage, "list_conversations", forbidden)
    dashboard_overview.render(
        object(), object(), "professional", True, False, navigate=lambda page: None
    )
