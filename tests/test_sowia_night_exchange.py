import pytest

def test_night_exchange_listing_validation_accepts_global_timezone():
    from cloud_storage import _validate_night_exchange_listing
    listing = _validate_night_exchange_listing(
        "App partenaire", "Singapour", "Asia/Singapore",
        ["Productivité"], "API de traduction", "Paiements", "21:00", "05:00"
    )
    assert listing["timezone"] == "Asia/Singapore"
    assert listing["night_start"] == "21:00"
    assert listing["night_end"] == "05:00"


def test_night_exchange_listing_validation_rejects_unknown_timezone():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Mars/Imaginary", ["Productivité"]
        )


def test_night_exchange_listing_validation_requires_category():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Europe/Paris", []
        )
