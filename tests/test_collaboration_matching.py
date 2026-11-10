import pytest

from collaboration_matching import match_companies, normalize_company


def company(name, offers=(), needs=(), objectives=("grow",), sector="Tech", country="France"):
    return {
        "name": name, "country": country, "sector": sector,
        "offers": list(offers), "needs": list(needs),
        "objectives": list(objectives), "website": "",
    }


def test_matches_two_complementary_companies():
    result = match_companies([
        company("Fabricant", offers=["capteurs", "production"], needs=["distribution"]),
        company("Distributeur", offers=["distribution"], needs=["capteurs"]),
    ])
    assert result.score > 0
    assert len(result.companies) == 2
    assert any("capteurs" in item for item in result.evidence)


def test_matches_three_or_more_companies_as_a_consortium():
    result = match_companies([
        company("A", offers=["logiciel"], needs=["vente"], objectives=["export"]),
        company("B", offers=["vente"], needs=["fabrication"], objectives=["export"], sector="Commerce"),
        company("C", offers=["fabrication"], needs=["logiciel"], objectives=["export"], sector="Industrie"),
    ])
    assert len(result.companies) == 3
    assert "Consortium" in result.suggested_model
    assert result.score <= 100


def test_requires_two_companies():
    with pytest.raises(ValueError, match="au moins deux"):
        match_companies([company("A", offers=["x"])])


def test_rejects_duplicate_company_names():
    with pytest.raises(ValueError, match="distincte"):
        match_companies([company("A", offers=["x"]), company("a", needs=["x"])])


def test_rejects_more_than_eight_companies():
    items = [company(f"Company {i}", offers=["x"]) for i in range(9)]
    with pytest.raises(ValueError, match="8 entreprises"):
        match_companies(items)


def test_rejects_invalid_website():
    with pytest.raises(ValueError, match="URL"):
        normalize_company(company("A", offers=["x"]) | {"website": "javascript:alert(1)"})


def test_requires_offer_or_need():
    with pytest.raises(ValueError, match="au moins une offre"):
        normalize_company(company("A"))


def test_non_complementary_companies_get_explicit_caveat():
    result = match_companies([
        company("A", offers=["wood"], needs=["steel"], objectives=["local"]),
        company("B", offers=["bread"], needs=["milk"], objectives=["tourism"]),
    ])
    assert any("Aucune complémentarité" in item for item in result.evidence)
