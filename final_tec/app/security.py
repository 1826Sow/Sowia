"""Credential helpers. Raw API keys are returned once and never stored."""
import hashlib
import hmac
import secrets

def generate_api_key() -> str:
    return "ftc_" + secrets.token_urlsafe(32)

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

def token_matches(provided: str | None, expected: str | None) -> bool:
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided, expected)
