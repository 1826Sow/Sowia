"""Regression checks for the Premium subscription preparation control."""
from pathlib import Path


def test_premium_preparation_uses_a_direct_button_without_navigation_callback():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('elif page == "Abonnement":')
    end = source.index('\n\nelif page == "SOWIA GLOBAL ID":', start)
    subscription_page = source[start:end]

    assert 'key="prepare_paypal_subscription"' in subscription_page
    assert "prepare_subscription_clicked = st.button(" in subscription_page
    assert "if prepare_subscription_clicked:" in subscription_page
    assert "st.form_submit_button(" not in subscription_page
    assert "request_paypal_subscription_navigation" not in source
    assert "_sowia_pending_navigation_page" not in source
