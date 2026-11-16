from pathlib import Path


def test_paypal_return_passes_normalized_order_id_to_edge_capture():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index("\n\ndef get_app_history", start)
    handler = source[start:end]

    assert "paypal_edge.invoke(" in handler
    assert '"capture"' in handler
    assert "str(paypal_token).strip()" in handler
    assert "premium_access.grant_paypal_entitlement(" not in handler
