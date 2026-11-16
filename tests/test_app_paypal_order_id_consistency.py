from pathlib import Path


def test_paypal_return_passes_normalized_order_id_to_edge_capture():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index("\n\ndef get_app_history", start)
    handler = source[start:end]

    normalize = handler.index('str(paypal_token).strip()')
    capture_call = handler.index('paypal_edge.invoke(')
    capture_action = handler.index('"capture"', capture_call)
    assert normalize < capture_call < capture_action
    assert 'supabase_client, "capture", str(paypal_token).strip()' in handler
    assert "premium_access.grant_paypal_entitlement(" not in handler
