


@pytest.mark.parametrize(
    "capture_result",
    [
        {"id": "OTHERORDER", "status": "COMPLETED"},
        {"id": "ORDER123", "status": "PENDING"},
        {
            "id": "ORDER123",
            "status": "COMPLETED",
            "purchase_units": [{
                "custom_id": "different-user",
                "reference_id": "sowia-premium",
                "amount": {"currency_code": "EUR", "value": "12.90"},
                "payments": {"captures": [{
                    "status": "COMPLETED",
                    "amount": {"currency_code": "EUR", "value": "12.90"},
                }]},
            }],
        },
    ],
)
def test_capture_rejects_incomplete_or_mismatched_capture_response(
    monkeypatch, capture_result
):
    _settings(monkeypatch)

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    monkeypatch.setattr(paypal, "_access_token", lambda config: "test-token")

    def fake_get(url, **kwargs):
        return Response({
            "id": "ORDER123",
            "intent": "CAPTURE",
            "status": "APPROVED",
            "purchase_units": [{
                "custom_id": "current-user",
                "reference_id": "sowia-premium",
                "amount": {"currency_code": "EUR", "value": "12.90"},
            }],
        })

    monkeypatch.setattr(paypal.requests, "get", fake_get)
    monkeypatch.setattr(paypal.requests, "post", lambda url, **kwargs: Response(capture_result))

    with pytest.raises(RuntimeError, match="capture PayPal"):
        paypal.capture_premium_order("ORDER123", "current-user")
