"""Regression tests for the short-lived Supabase PKCE verifier storage."""
import time

import sowia_supabase_auth as auth


def test_pkce_verifier_survives_new_storage_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_OAUTH_DB", tmp_path / "oauth.sqlite3")
    first = auth._BrowserScopedOAuthStorage("browser-a")
    first.set_item("sb-project-auth-token-code-verifier", "test-verifier")

    # The OAuth callback may create a fresh SDK client and storage adapter.
    second = auth._BrowserScopedOAuthStorage("browser-a")
    assert second.get_item("sb-project-auth-token-code-verifier") == "test-verifier"


def test_pkce_verifier_is_isolated_by_browser(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_OAUTH_DB", tmp_path / "oauth.sqlite3")
    auth._BrowserScopedOAuthStorage("browser-a").set_item(
        "sb-project-auth-token-code-verifier", "secret-a"
    )

    other_browser = auth._BrowserScopedOAuthStorage("browser-b")
    assert other_browser.get_item("sb-project-auth-token-code-verifier") is None


def test_pkce_verifier_can_be_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_OAUTH_DB", tmp_path / "oauth.sqlite3")
    storage = auth._BrowserScopedOAuthStorage("browser-a")
    storage.set_item("sb-project-auth-token-code-verifier", "one-time")
    storage.remove_item("sb-project-auth-token-code-verifier")

    assert storage.get_item("sb-project-auth-token-code-verifier") is None


def test_expired_pkce_verifier_is_not_returned(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "_OAUTH_DB", tmp_path / "oauth.sqlite3")
    storage = auth._BrowserScopedOAuthStorage("browser-a")
    storage.set_item("sb-project-auth-token-code-verifier", "expired")
    with storage._connect() as conn:
        conn.execute(
            "UPDATE oauth_pkce_verifiers SET expires_at=?",
            (int(time.time()) - 1,),
        )

    assert storage.get_item("sb-project-auth-token-code-verifier") is None
