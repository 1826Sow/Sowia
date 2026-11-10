import pytest

from business_cards import build_printable_card_html, build_vcard, validate_business_card


def sample(**overrides):
    data = {
        "display_name": "Alex Martin",
        "job_title": "Directeur",
        "company": "SOWIA Conseil",
        "email": "alex@example.com",
        "phone": "+33123456789",
        "website": "https://example.com",
        "country": "France",
        "style": "Noir & or",
    }
    data.update(overrides)
    return data


def test_validates_and_trims_card_fields():
    card = validate_business_card(sample(display_name="  Alex Martin  "))
    assert card["display_name"] == "Alex Martin"


def test_requires_name_and_company_or_role():
    with pytest.raises(ValueError):
        validate_business_card(sample(display_name=" "))
    with pytest.raises(ValueError):
        validate_business_card(sample(job_title="", company=""))


def test_rejects_invalid_email_and_website():
    with pytest.raises(ValueError):
        validate_business_card(sample(email="not-an-email"))
    with pytest.raises(ValueError):
        validate_business_card(sample(website="javascript:alert(1)"))


def test_vcard_contains_contact_fields():
    result = build_vcard(sample())
    assert "BEGIN:VCARD" in result
    assert "FN:Alex Martin" in result
    assert "ORG:SOWIA Conseil" in result
    assert "EMAIL;TYPE=WORK:alex@example.com" in result
    assert "END:VCARD" in result


def test_html_is_printable_and_escapes_user_content():
    result = build_printable_card_html(sample(display_name="<Alex>"))
    assert "@page { size: 90mm 50mm; margin: 0; }" in result
    assert "&lt;Alex&gt;" in result
    assert "<Alex>" not in result
