"""Unit checks for the synthetic-only Financial Command Center prototype."""
import financial_command_center_ui as dashboard


def test_each_entity_has_its_own_currency_and_scenario():
    assert set(dashboard.ENTITIES) == {"SOWIA", "FINAL TEC PLATFORM", "EDGE FINDS"}
    assert dashboard.ENTITIES["SOWIA"]["currency"] == "EUR"
    assert dashboard.ENTITIES["FINAL TEC PLATFORM"]["currency"] == "USD"
    assert dashboard.ENTITIES["EDGE FINDS"]["currency"] == "EUR"


def test_scenario_values_are_non_negative_and_separate():
    for entity in dashboard.ENTITIES.values():
        scenario = entity["scenario"]
        assert all(value >= 0 for value in scenario.values())
        assert set(scenario) == {"inflow", "fees", "refunds", "pending", "anomalies"}


def test_demo_events_are_explicitly_synthetic_and_scoped():
    assert dashboard.SAMPLE_EVENTS
    for event in dashboard.SAMPLE_EVENTS:
        assert event["Référence"].startswith("DEMO-")
        assert event["Entité"] in dashboard.ENTITIES
        assert event["Statut"] in {"À rapprocher", "Scénario fictif", "Anomalie simulée"}
