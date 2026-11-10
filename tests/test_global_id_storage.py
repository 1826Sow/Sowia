import pytest

from cloud_storage import _validate_global_profile


def test_global_profile_requires_public_name_country_and_org_or_app():
    with pytest.raises(ValueError):
        _validate_global_profile("A", country="France", organization="SOWIA")
    with pytest.raises(ValueError):
        _validate_global_profile("SOWIA", country="", organization="SOWIA")
    with pytest.raises(ValueError):
        _validate_global_profile("SOWIA", country="France")


def test_global_profile_normalizes_languages_and_rejects_http_website():
    result = _validate_global_profile(
        "SOWIA", organization="SOWIA", country="France",
        languages="fr, en, fr", website="https://sowia.example"
    )
    assert result["languages"] == ["fr", "en"]
    with pytest.raises(ValueError):
        _validate_global_profile(
            "SOWIA", organization="SOWIA", country="France",
            website="http://sowia.example"
        )


def test_global_profile_is_private_unless_explicitly_published():
    result = _validate_global_profile(
        "SOWIA", organization="SOWIA", country="France"
    )
    assert result["is_published"] is False
