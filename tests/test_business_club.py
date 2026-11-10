import pytest
from business_club import match_profile, validate_profile, validate_request

def profile(name, country="France", offers=(), needs=(), objectives=("export",), **extra):
    return {"company_name": name, "country": country, "sector": "Tech", "description": "Présentation",
            "offers": list(offers), "needs": list(needs), "objectives": list(objectives),
            "website": "", "is_published": True, **extra}

def test_validates_opt_in_profile():
    assert validate_profile(profile("Société A", offers=["logiciel"]))["is_published"] is True

def test_requires_company_and_value_proposition():
    with pytest.raises(ValueError, match="Nom de l'entreprise"):
        validate_profile(profile("", offers=["x"]))
    with pytest.raises(ValueError, match="au moins une offre"):
        validate_profile(profile("A", objectives=[]))

def test_rejects_unsafe_website():
    with pytest.raises(ValueError, match="URL"):
        validate_profile(profile("A", offers=["x"], website="javascript:alert(1)"))

def test_matches_complementary_offers_and_needs():
    result = match_profile(profile("A", offers=["capteurs"], needs=["distribution"]),
                           profile("B", offers=["distribution"], needs=["capteurs"]))
    assert result.score == 50
    assert result.recommendation == "Proposer une rencontre exploratoire"

def test_shared_objective_adds_transparent_score():
    result = match_profile(profile("A", offers=["logiciel"], objectives=["export"]),
                           profile("B", needs=["bois"], objectives=["export"], country="Canada"))
    assert result.score == 15
    assert any("deux pays" in item for item in result.evidence)

def test_request_message_is_bounded_and_required():
    assert validate_request("Bonjour, échangeons.") == "Bonjour, échangeons."
    with pytest.raises(ValueError):
        validate_request(" ")

def test_unpublished_flag_must_be_boolean():
    with pytest.raises(ValueError, match="publication"):
        validate_profile(profile("A", offers=["x"], is_published="yes"))
