"""Tests for Premium extended-memory access and length limits."""
import pytest

import premium_memory


def test_extended_memory_checks_entitlement_before_database_write(monkeypatch):
    calls = []

    def guard(client, user, feature):
        calls.append(("guard", client, user, feature))

    def save(client, user, content, max_chars):
        calls.append(("save", client, user, content, max_chars))
        return "saved"

    monkeypatch.setattr(premium_memory, "require_feature_access", guard)
    monkeypatch.setattr(premium_memory.cloud_storage, "add_memory", save)
    result = premium_memory.add_extended_memory("client", "user", "x" * 2000)

    assert result == "saved"
    assert calls[0] == ("guard", "client", "user", "extended_memory")
    assert calls[1] == ("save", "client", "user", "x" * 2000, 5000)


def test_extended_memory_denies_before_database_write(monkeypatch):
    def deny(*args, **kwargs):
        raise PermissionError("Premium requis")

    def unexpected_save(*args, **kwargs):
        raise AssertionError("Database write must not happen without Premium")

    monkeypatch.setattr(premium_memory, "require_feature_access", deny)
    monkeypatch.setattr(premium_memory.cloud_storage, "add_memory", unexpected_save)
    with pytest.raises(PermissionError, match="Premium requis"):
        premium_memory.add_extended_memory("client", "user", "Note privée")


@pytest.mark.parametrize("value", ["", "   "])
def test_extended_memory_rejects_empty_note(value):
    with pytest.raises(ValueError, match="ne peut pas être vide"):
        premium_memory.add_extended_memory("client", "user", value)


def test_extended_memory_rejects_more_than_5000_characters(monkeypatch):
    monkeypatch.setattr(
        premium_memory, "require_feature_access",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("Guard must not run for invalid input")),
    )
    with pytest.raises(ValueError, match="5 000"):
        premium_memory.add_extended_memory("client", "user", "x" * 5001)
