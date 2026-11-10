import pytest
from datetime import date
from printer_network import compare_printer_quotes, validate_printer_candidate, validate_printer_quote

def supplier(**overrides):
    data = {"name": "Imprimerie Exemple", "country": "France", "website": "https://example.com",
            "capabilities": ["Cartes 90 × 50 mm"]}
    data.update(overrides)
    return validate_printer_candidate(data)

def quote(supplier_id, **overrides):
    data = {"supplier_id": supplier_id, "destination_country": "France", "quantity": 500,
            "currency": "EUR", "printing_cost": "45.50", "shipping_cost": "8.90",
            "lead_days": 5, "paper_finish": "350 g/m², mat", "valid_until": "2099-12-31"}
    data.update(overrides)
    return validate_printer_quote(data)

def test_supplier_is_always_candidate_on_submission():
    assert supplier(status="verified")["status"] == "candidate"

def test_rejects_non_https_supplier_site():
    with pytest.raises(ValueError):
        supplier(website="http://example.com")

def test_quote_amounts_and_currency_are_normalized():
    item = supplier()
    q = quote(item["id"], currency="eur")
    assert q["currency"] == "EUR"
    assert str(q["printing_cost"]) == "45.50"

def test_rejects_invalid_quote_quantity_and_expiry():
    item = supplier()
    with pytest.raises(ValueError):
        quote(item["id"], quantity=0)
    with pytest.raises(ValueError):
        quote(item["id"], valid_until="not-a-date")

def test_comparison_is_like_for_like_and_never_auto_validates():
    item = supplier()
    q = quote(item["id"])
    rows = compare_printer_quotes([item], [q], "France", 500, "EUR", today=date(2026, 1, 1))
    assert len(rows) == 1
    assert rows[0]["total_cost"] == q["printing_cost"] + q["shipping_cost"]
    assert rows[0]["eligible_for_order"] is False
    assert rows[0]["reason"] == "Imprimeur à vérifier"

def test_comparison_excludes_other_destination_quantity_and_currency():
    item = supplier()
    q = quote(item["id"])
    assert compare_printer_quotes([item], [q], "Belgique", 500, "EUR") == []
    assert compare_printer_quotes([item], [q], "France", 250, "EUR") == []
    assert compare_printer_quotes([item], [q], "France", 500, "USD") == []
