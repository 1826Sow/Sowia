from pathlib import Path


def test_one_time_premium_checkout_is_available_on_subscription_page():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('elif page == "Abonnement":')
    end = source.find('\n\nelif page == ', start + 1)
    page = source[start:end if end != -1 else len(source)]

    assert "paypal_payments.paypal_configuration()" in page
    assert "paypal_payments.create_premium_order(" in page
    assert "buy_sowia_premium_one_time" in page
    assert "Continuer vers le paiement PayPal" in page
    assert "Aucun accès Premium n’a été accordé." in page


def test_one_time_checkout_keeps_monthly_subscription_separate():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('elif page == "Abonnement":')
    end = source.find('\n\nelif page == ', start + 1)
    page = source[start:end if end != -1 else len(source)]

    assert page.index("paypal_payments.create_premium_order(") < page.index(
        "paypal_subscriptions.paypal_subscription_configuration()"
    )
