from pathlib import Path


def test_paypal_return_requires_authenticated_cloud_user_and_uses_edge_function():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index("\n\ndef get_app_history", start)
    handler = source[start:end]

    assert 'paypal_edge.invoke(' in handler
    assert '"capture"' in handler
    assert "premium_access.create_admin_client()" not in handler
    assert "premium_access.grant_paypal_entitlement(" not in handler
    assert "Le paiement n'a pas pu être confirmé." in handler
    assert "Aucun accès Premium " in handler
    assert "n'a été accordé automatiquement." in handler
