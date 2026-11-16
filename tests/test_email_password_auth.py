"""Tests for SOW IA email/password authentication."""
import pytest
import sowia_supabase_auth as supabase_auth


def test_password_sign_in_normalizes_email_and_delegates_to_supabase():
    calls = []

    class Auth:
        def sign_in_with_password(self, payload):
            calls.append(payload)
            return "authenticated"

    client = type("Client", (), {"auth": Auth()})()
    result = supabase_auth.sign_in_email_password(
        client, "  USER@EXAMPLE.COM ", "a-secure-password"
    )

    assert result == "authenticated"
    assert calls == [{
        "email": "user@example.com",
        "password": "a-secure-password",
    }]


@pytest.mark.parametrize("email", ["", "invalid", "x" * 255])
def test_password_sign_in_rejects_invalid_email(email):
    with pytest.raises(ValueError, match="Adresse e-mail invalide"):
        supabase_auth.sign_in_email_password(object(), email, "password")


def test_password_sign_in_rejects_empty_password():
    with pytest.raises(ValueError, match="mot de passe"):
        supabase_auth.sign_in_email_password(object(), "user@example.com", "")
