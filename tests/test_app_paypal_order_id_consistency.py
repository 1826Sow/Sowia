from pathlib import Path


def test_paypal_return_uses_normalized_order_id_for_capture_and_entitlement():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index("\n\ndef get_app_history", start)
    handler = source[start:end]

    normalize = handler.index('normalized_order_id = str(paypal_token).strip()')
    capture_call = handler.index("paypal_payments.capture_premium_order(")
    capture_arg = handler.index("normalized_order_id", capture_call)
    grant_call = handler.index("premium_access.grant_paypal_entitlement(")
    grant_arg = handler.index("normalized_order_id", grant_call)

    assert normalize < capture_call < capture_arg < grant_call < grant_arg
    assert "str(paypal_token)" not in handler[capture_call:grant_call]
