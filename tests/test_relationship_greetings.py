from datetime import date

import pytest

from relationship_greetings import (
    COUNTRY_DEFAULTS, OCCASIONS, SUPPORTED_LANGUAGES,
    build_greeting, default_language, national_day, upcoming_fixed_occasions,
)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
@pytest.mark.parametrize("occasion", OCCASIONS)
def test_greeting_exists_for_each_supported_language_and_occasion(language, occasion):
    message = build_greeting(language, occasion, "Alex", "Example Ltd", "France")
    assert message.strip()
    assert "SOW IA" in message


def test_country_language_defaults():
    assert default_language("France") == "Français"
    assert default_language("China") == "中文"
    assert default_language("United Arab Emirates") == "العربية"
    assert default_language("Unknown country") == "English"


def test_fixed_calendar_uses_country_specific_national_day():
    france = upcoming_fixed_occasions("France", 2027)
    assert {"occasion": "Fête nationale", "date": "2027-07-14"} in france
    assert {"occasion": "Noël", "date": "2027-12-25"} in france
    assert national_day("France") == "14 juillet"


def test_movable_holidays_are_not_assigned_unverified_dates():
    assert all(
        item["occasion"] not in {"Fête de fin de Ramadan / Aïd el-Fitr", "Aïd el-Adha", "Nouvel An lunaire", "Diwali"}
        for item in upcoming_fixed_occasions("France", 2027)
    )


def test_invalid_language_and_occasion_rejected():
    with pytest.raises(ValueError):
        build_greeting("Klingon", "Noël")
    with pytest.raises(ValueError):
        build_greeting("Français", "Occasion inventée")
