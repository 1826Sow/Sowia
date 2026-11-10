import pytest
from vip_card_orders import validate_vip_card_order

def valid(**updates):
    data = {"cardholder_name":"Camille Martin","company":"Atelier CM",
            "destination_country":"France","style":"Noir & or","quantity":500,"notes":""}
    data.update(updates)
    return validate_vip_card_order(data)

def test_valid_order_starts_as_request_not_payment():
    order = valid()
    assert order["status"] == "requested"
    assert order["quantity"] == 500

@pytest.mark.parametrize("quantity", [0, 49, 10001, True, 2.5])
def test_rejects_invalid_quantities(quantity):
    with pytest.raises(ValueError):
        valid(quantity=quantity)

def test_rejects_unsupported_style():
    with pytest.raises(ValueError):
        valid(style="Style inventé")

def test_rejects_missing_destination():
    with pytest.raises(ValueError):
        valid(destination_country=" ")

def test_limits_free_text():
    with pytest.raises(ValueError):
        valid(notes="x" * 1001)
