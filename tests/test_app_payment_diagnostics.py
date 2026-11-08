from pathlib import Path


def test_payment_errors_do_not_render_raw_exception_details():
    source = Path("app.py").read_text(encoding="utf-8")

    protected_messages = (
        "Le paiement n'a pas pu être confirmé. Aucun accès Premium n'a été accordé.",
        "Impossible de vérifier votre abonnement auprès de Supabase.",
        "Impossible de préparer le paiement PayPal.",
    )
    for message in protected_messages:
        position = source.index(message)
        nearby = source[position:position + 250]
        assert "st.caption(str(exc))" not in nearby
        assert "st.exception(exc)" not in nearby
