from pathlib import Path


def test_paypal_return_checks_payment_enablement_before_admin_client():
    source = Path("app.py").read_text(encoding="utf-8")
    start = source.index('if cloud_mode and current_user is not None:')
    end = source.index('\n\ndef get_app_history', start)
    handler = source[start:end]

    config_check = handler.index("payment_config = paypal_payments.paypal_configuration()")
    disabled_guard = handler.index("if payment_config is None:")
    admin_client = handler.index("premium_access.create_admin_client()")
    capture = handler.index("paypal_payments.capture_premium_order(")

    assert config_check < disabled_guard < admin_client < capture
