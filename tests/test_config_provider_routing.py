"""Tests for provider-specific API endpoint routing."""
from config import _provider_base_url


def test_groq_key_always_uses_groq_endpoint_even_with_legacy_openai_url():
    assert _provider_base_url(
        "configured-groq-key",
        "https://api.openai.com/v1",
    ) == "https://api.groq.com/openai/v1"


def test_openai_key_keeps_configured_openai_endpoint():
    assert _provider_base_url(
        "",
        "https://custom-openai-compatible.example/v1",
    ) == "https://custom-openai-compatible.example/v1"


def test_openai_key_without_custom_endpoint_uses_sdk_default():
    assert _provider_base_url("", None) is None
