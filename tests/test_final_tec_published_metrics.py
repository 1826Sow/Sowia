from types import SimpleNamespace

from final_tec_access import fetch_published_final_tec_metrics


class Query:
    def __init__(self, rows=None, error=None):
        self.rows = rows
        self.error = error
        self.filters = []
        self.selected = None
        self.ordered = None
        self.limit_value = None

    def select(self, columns):
        self.selected = columns
        return self

    def eq(self, key, value):
        self.filters.append((key, value))
        return self

    def order(self, key, desc=False):
        self.ordered = (key, desc)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.rows)


class FakeSupabase:
    def __init__(self, query):
        self.query = query
        self.table_name = None

    def table(self, table_name):
        self.table_name = table_name
        return self.query


def valid_verified_row(**overrides):
    row = {
        "id": "metric-1",
        "metric_key": "latency",
        "title": "Latence mesurée",
        "category": "performance",
        "metric_value": 42,
        "unit": "ms",
        "evidence_status": "verified",
        "source_url": "https://example.org/benchmark",
        "observed_at": "2026-11-10T10:00:00Z",
        "evidence_ref": "BENCH-001",
        "evidence_owner": "Équipe technique",
        "assumptions": None,
        "horizon": None,
        "synthetic_label": None,
        "publication_state": "published",
        "published_at": "2026-11-11T09:00:00Z",
    }
    row.update(overrides)
    return row


def test_fetch_returns_only_valid_published_metrics_and_applies_filters():
    query = Query(rows=[
        valid_verified_row(),
        valid_verified_row(id="draft", publication_state="draft"),
        valid_verified_row(id="bad-source", source_url="http://example.org"),
        valid_verified_row(id="pending", evidence_status="pending"),
    ])
    client = FakeSupabase(query)

    rows = fetch_published_final_tec_metrics(client)

    assert client.table_name == "final_tec_published_metrics"
    assert ("project_key", "final-tec") in query.filters
    assert ("publication_state", "published") in query.filters
    assert query.ordered == ("published_at", True)
    assert query.limit_value == 500
    assert [row["id"] for row in rows] == ["metric-1"]
    assert rows[0]["display_status"] == "Mesuré et vérifié"


def test_projected_metric_requires_hypotheses_and_horizon():
    query = Query(rows=[
        valid_verified_row(
            evidence_status="projected",
            source_url=None,
            observed_at=None,
            evidence_ref=None,
            evidence_owner=None,
            assumptions="Hypothèse de charge constante",
            horizon="T2 2027",
        )
    ])
    rows = fetch_published_final_tec_metrics(FakeSupabase(query))

    assert len(rows) == 1
    assert rows[0]["display_status"] == "Projection — hypothèses déclarées"


def test_synthetic_metric_must_be_labeled():
    query = Query(rows=[
        valid_verified_row(
            evidence_status="synthetic",
            source_url=None,
            observed_at=None,
            evidence_ref=None,
            evidence_owner=None,
            synthetic_label="Démonstration fictive",
        ),
        valid_verified_row(
            id="unlabeled",
            evidence_status="synthetic",
            source_url=None,
            observed_at=None,
            evidence_ref=None,
            evidence_owner=None,
            synthetic_label=None,
        ),
    ])
    rows = fetch_published_final_tec_metrics(FakeSupabase(query))

    assert [row["id"] for row in rows] == ["metric-1"]
    assert rows[0]["display_status"] == "Démonstration fictive"


def test_missing_or_failed_live_source_returns_none_not_demo_values():
    assert fetch_published_final_tec_metrics(None) is None
    failed = Query(error=RuntimeError("database unavailable"))
    assert fetch_published_final_tec_metrics(FakeSupabase(failed)) is None


def test_empty_published_registry_returns_empty_list():
    assert fetch_published_final_tec_metrics(FakeSupabase(Query(rows=[]))) == []
