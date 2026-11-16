from pathlib import Path


def _subscription_page():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('elif page == "Abonnement":')
    end = source.find("\n\nelif page == ", start + 1)
    return source[start:end if end != -1 else len(source)]


def test_one_time_premium_checkout_uses_authenticated_edge_function():
    page = _subscription_page()

    assert "paypal_edge.checkout_enabled()" in page
    assert 'paypal_edge.invoke(supabase_client, "create")' in page
    assert 'key="buy_sowia_premium_one_time"' in page
    assert "Continuer vers le paiement PayPal" in page
    assert "Aucun accès Premium n’a été accordé." in page
    assert "paypal_payments.create_premium_order(" not in page


def test_one_time_checkout_keeps_monthly_subscription_separate():
    page = _subscription_page()

    assert page.index('paypal_edge.invoke(supabase_client, "create")') < page.index(
        "paypal_subscriptions.paypal_subscription_configuration()"
    )
    assert "Abonnement mensuel" in page
