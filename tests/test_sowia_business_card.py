import pytest

from sowia_business_card import BusinessCardError, build_vcard


def sample():
    return {
        "display_name": "SOWIA Partner",
        "organization": "SOWIA",
        "country": "France",
        "website": "https://sowia.example",
        "public_id": "SOWIA-ABC123",
    }


def test_vcard_contains_only_supplied_public_contact_fields():
    card = build_vcard(sample(), email="contact@sowia.example", phone="+33123456789")
    assert "FN:SOWIA Partner" in card
    assert "ORG:SOWIA" in card
    assert "EMAIL;TYPE=WORK:contact@sowia.example" in card
    assert "TEL;TYPE=WORK,VOICE:+33123456789" in card
    assert "BEGIN:VCARD" in card and "END:VCARD" in card


def test_vcard_rejects_invalid_email_and_non_https_website():
    with pytest.raises(BusinessCardError):
        build_vcard(sample(), email="not-an-email")
    bad = sample()
    bad["website"] = "http://sowia.example"
    with pytest.raises(BusinessCardError):
        build_vcard(bad)


def test_vcard_requires_a_professional_name():
    with pytest.raises(BusinessCardError):
        build_vcard({"display_name": " "})
