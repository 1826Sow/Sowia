"""Fail-closed HTTPS JWKS resolver for FINAL TEC.

The caller must explicitly allow both issuer and JWKS origins. TLS verification is always
enabled by urllib's default SSL context; redirects are rejected; responses and
cache lifetimes are bounded. This module does not select an identity provider.
"""
from __future__ import annotations

import json
import re
import threading
import time
from http.client import HTTPException
from email.message import Message
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

import jwt


class JWKSConfigurationError(ValueError):
    """Raised when JWKS trust configuration is unsafe."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _https_origin(url: str) -> tuple[str, str, int]:
    if not isinstance(url, str) or not url:
        raise JWKSConfigurationError("URL is required")
    parsed = urlsplit(url)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise JWKSConfigurationError("URL must be HTTPS without credentials, query or fragment")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise JWKSConfigurationError("URL port is invalid") from exc
    return ("https", parsed.hostname.lower().rstrip("."), port)


class HTTPSJWKSResolver:
    """Resolve RS256 public keys from one explicitly allowlisted HTTPS origin.

    Unknown kids trigger one bounded refresh. A still-unknown kid fails closed.
    opener is injectable for tests; production defaults use urllib TLS
    verification and a redirect handler that refuses all redirects.
    """

    def __init__(
        self,
        *,
        issuer: str,
        jwks_url: str,
        allowed_origins: Iterable[str],
        cache_ttl_seconds: int = 300,
        max_cache_ttl_seconds: int = 900,
        timeout_seconds: float = 3.0,
        max_response_bytes: int = 262144,
        clock: Callable[[], float] = time.time,
        opener: Any | None = None,
    ) -> None:
        issuer_origin = _https_origin(issuer)
        jwks_origin = _https_origin(jwks_url)
        allowed = {_https_origin(item) for item in allowed_origins}
        if not allowed or issuer_origin not in allowed or jwks_origin not in allowed:
            raise JWKSConfigurationError("Issuer and JWKS origins must both be explicitly allowlisted")
        if isinstance(cache_ttl_seconds, bool) or not isinstance(cache_ttl_seconds, int) or cache_ttl_seconds <= 0:
            raise JWKSConfigurationError("cache_ttl_seconds must be a positive integer")
        if isinstance(max_cache_ttl_seconds, bool) or not isinstance(max_cache_ttl_seconds, int) or max_cache_ttl_seconds <= 0:
            raise JWKSConfigurationError("max_cache_ttl_seconds must be a positive integer")
        if max_cache_ttl_seconds < cache_ttl_seconds:
            raise JWKSConfigurationError("maximum cache TTL cannot be below the default TTL")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise JWKSConfigurationError("timeout_seconds must be positive")
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int) or max_response_bytes < 1024:
            raise JWKSConfigurationError("max_response_bytes must be at least 1024")
        self.issuer = issuer
        self.jwks_url = jwks_url
        self.issuer_origin = issuer_origin
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_ttl_seconds = max_cache_ttl_seconds
        self.timeout_seconds = float(timeout_seconds)
        self.max_response_bytes = max_response_bytes
        self.clock = clock
        self._opener = opener or build_opener(HTTPSHandler(), _RejectRedirects())
        self._lock = threading.RLock()
        self._keys: dict[str, Any] = {}
        self._expires_at = 0.0

    def __call__(self, kid: str) -> Any | None:
        if not isinstance(kid, str) or not kid or len(kid) > 256:
            return None
        with self._lock:
            if self.clock() >= self._expires_at:
                self._refresh()
            key = self._keys.get(kid)
            if key is None:
                self._refresh()
                key = self._keys.get(kid)
            return key

    def _refresh(self) -> None:
        request = Request(
            self.jwks_url,
            headers={"Accept": "application/json", "User-Agent": "SOWIA-FINAL-TEC-JWKS/1"},
            method="GET",
        )
        try:
            response = self._opener.open(request, timeout=self.timeout_seconds)
            with response:
                if response.getcode() != 200:
                    raise JWKSConfigurationError("JWKS endpoint did not return HTTP 200")
                content_type = response.headers.get("Content-Type", "")
                media_type = content_type.split(";", 1)[0].strip().lower()
                if not re.fullmatch(
                    r"application/(?:json|[!#$%&'*+.^_\x60|~0-9a-z-]+\\+json)",
                    media_type,
                ):
                    raise JWKSConfigurationError("JWKS response is not an accepted JSON media type")
                raw = response.read(self.max_response_bytes + 1)
                if len(raw) > self.max_response_bytes:
                    raise JWKSConfigurationError("JWKS response exceeds configured size limit")
                cache_ttl = self._response_ttl(response.headers)
        except HTTPError as exc:
            raise JWKSConfigurationError("JWKS endpoint returned an HTTP error or redirect") from exc
        except (URLError, HTTPException, TimeoutError, OSError) as exc:
            # Includes failures during body reads. Never fall back to expired
            # keys and never expose provider/network details to callers.
            raise JWKSConfigurationError("JWKS endpoint could not be reached safely") from exc
        try:
            document = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise JWKSConfigurationError("JWKS response is invalid JSON") from exc
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise JWKSConfigurationError("JWKS document must contain a keys array")
        parsed: dict[str, Any] = {}
        seen: set[str] = set()
        for item in document["keys"]:
            if not isinstance(item, dict):
                raise JWKSConfigurationError("JWKS key entry must be an object")
            item_kid = item.get("kid")
            if not isinstance(item_kid, str) or not item_kid:
                continue
            if item_kid in seen:
                raise JWKSConfigurationError("JWKS contains duplicate key identifiers")
            seen.add(item_kid)
            if (
                item.get("kty") != "RSA"
                or item.get("alg") not in (None, "RS256")
                or item.get("use") not in (None, "sig")
                or ("key_ops" in item and (not isinstance(item["key_ops"], list) or "verify" not in item["key_ops"]))
                or not isinstance(item.get("n"), str)
                or not isinstance(item.get("e"), str)
            ):
                continue
            # A verification-only JWKS must never expose private RSA material.
            # Reject the whole document rather than silently accepting a mixed
            # public/private key set from an identity authority.
            if any(name in item for name in ("d", "p", "q", "dp", "dq", "qi", "oth")):
                raise JWKSConfigurationError("JWKS must not contain private RSA parameters")
            try:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(item))
            except (ValueError, TypeError, KeyError):
                continue
            # Enforce modern RSA strength and a conventional public exponent.
            if getattr(public_key, "key_size", 0) < 2048:
                raise JWKSConfigurationError("JWKS RSA keys must be at least 2048 bits")
            if public_key.public_numbers().e < 65537 or public_key.public_numbers().e % 2 == 0:
                raise JWKSConfigurationError("JWKS RSA public exponent is too weak")
            parsed[item_kid] = public_key
        if not parsed:
            raise JWKSConfigurationError("JWKS contains no usable RS256 RSA verification keys")
        self._keys = parsed
        self._expires_at = self.clock() + min(cache_ttl, self.max_cache_ttl_seconds)

    def _response_ttl(self, headers: Message) -> int:
        cache_control = headers.get("Cache-Control", "")
        directives = [part.strip() for part in cache_control.split(",")]
        parsed_directives = [part.split("=", 1) for part in directives]

        # This resolver has no conditional revalidation path. Do not reuse a
        # response that the origin says must not be stored or revalidated.
        if any(parts[0].strip().lower() in {"no-store", "no-cache"} for parts in parsed_directives):
            return 0

        max_age_values = [
            parts[1].strip()
            for parts in parsed_directives
            if parts[0].strip().lower() == "max-age" and len(parts) == 2
        ]
        malformed_max_age = any(
            parts[0].strip().lower() == "max-age" and len(parts) != 2
            for parts in parsed_directives
        )
        # Duplicate or malformed freshness directives are ambiguous. Fail
        # closed instead of applying a potentially more permissive default.
        if malformed_max_age or len(max_age_values) > 1:
            return 0
        if max_age_values:
            value = max_age_values[0]
            if value.startswith('"') or value.endswith('"'):
                if not (value.startswith('"') and value.endswith('"') and len(value) >= 2):
                    return 0
                value = value[1:-1]
            # HTTP delta-seconds uses ASCII digits. Bound the length before
            # int() so an attacker cannot trigger huge-integer parsing costs.
            if not value.isascii() or not value.isdecimal() or len(value) > 10:
                return 0
            return min(int(value), self.max_cache_ttl_seconds)
        return self.cache_ttl_seconds
