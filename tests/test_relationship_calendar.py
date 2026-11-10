from datetime import date

import pytest

from relationship_calendar import (
    EVENT_TYPES, classify_event, validate_event,
)


def test_validate_event_normalizes_fields():
    result = validate_event(
        "  Appeler partenaire  ", "Relance commerciale", "2027-03-04",
        "  Préparer le dossier  ", True,
    )
    assert result == {
        "title": "Appeler partenaire",
        "event_type": "Relance commerciale",
        "due_date": "2027-03-04",
        "notes": "Préparer le dossier",
        "contact_authorized": True,
    }


@pytest.mark.parametrize("title", ["", " " , "x" * 161])
def test_invalid_title_rejected(title):
    with pytest.raises(ValueError):
        validate_event(title, EVENT_TYPES[0], "2027-03-04")


def test_invalid_type_and_date_rejected():
    with pytest.raises(ValueError):
        validate_event("Rappel", "Type inconnu", "2027-03-04")
    with pytest.raises(ValueError):
        validate_event("Rappel", EVENT_TYPES[0], "04/03/2027")


def test_contact_authorization_is_explicit_boolean():
    with pytest.raises(ValueError):
        validate_event("Rappel", EVENT_TYPES[0], "2027-03-04", contact_authorized="yes")
    assert validate_event("Rappel", EVENT_TYPES[0], "2027-03-04")["contact_authorized"] is False


def test_event_classification():
    today = date(2027, 3, 4)
    assert classify_event("2027-03-03", today=today) == "En retard"
    assert classify_event("2027-03-04", today=today) == "Aujourd'hui"
    assert classify_event("2027-03-05", today=today) == "À venir"
    assert classify_event("2027-03-05", "Terminé", today=today) == "Terminé"
    assert classify_event("2027-03-05", "Annulé", today=today) == "Annulé"
