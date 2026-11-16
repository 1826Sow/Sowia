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

@pytest.mark.parametrize("otp_type", ["signup", "email", "magiclink"])
def test_email_confirmation_verifies_supported_token_hash_types(otp_type):
    calls = []

    class Auth:
        def verify_otp(self, payload):
            calls.append(payload)
            return "verified"

    client = type("Client", (), {"auth": Auth()})()
    result = supabase_auth.complete_email_magic_link(client, "one-time-token", otp_type)

    assert result == "verified"
    assert calls == [{"token_hash": "one-time-token", "type": otp_type}]


@pytest.mark.parametrize(
    ("token_hash", "otp_type"),
    [("", "signup"), ("x" * 4097, "signup"), ("one-time-token", "unknown")],
)
def test_email_confirmation_rejects_invalid_token_or_type(token_hash, otp_type):
    with pytest.raises(ValueError, match="Lien de connexion invalide"):
        supabase_auth.complete_email_magic_link(object(), token_hash, otp_type)

def test_email_callback_clears_one_time_token_from_query_and_fragment():
    import inspect

    source = inspect.getsource(supabase_auth.read_email_auth_fragment)
    assert 'query.delete("token_hash")' in source
    assert 'fragment.delete("token_hash")' in source
    assert 'fragment.delete("type")' in source

def test_email_callback_clears_session_tokens_from_query_and_fragment():
    import inspect

    source = inspect.getsource(supabase_auth.read_email_auth_fragment)
    assert 'for (const name of ["access_token", "refresh_token", "type"])' in source
    assert 'query.delete(name)' in source
    assert 'fragment.delete(name)' in source

