from pathlib import Path


def test_paypal_return_stores_the_same_normalized_order_id_it_captures():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index("\n\ndef get_app_history", start)
    handler = source[start:end]

    normalize = handler.index('normalized_order_id = str(paypal_token).strip()')
    capture = handler.index(
        "paypal_payments.capture_premium_order(normalized_order_id,"
    )
    grant = handler.index(
        "admin_client, str(current_user.id), normalized_order_id,"
    )

    assert normalize < capture < grant
    assert "grant_paypal_entitlement(\n                admin_client, str(current_user.id), str(paypal_token)" not in handler
