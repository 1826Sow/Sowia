"""Provider-neutral OIDC identity verifier for FINAL TEC approval callbacks.

The verifier accepts only RS256 ID tokens from one configured issuer/audience.
Signing keys, server-side approval sessions, and current role assignments are
injected from trusted services; none are read from the submitted approval.
"""
from __future__ import annotations

import hmac
import math
import time
from urllib.parse import urlsplit
from typing import Any, Callable, Mapping

import jwt
from jwt import InvalidTokenError


class OIDCIdentityError(ValueError):
    """Raised for invalid OIDC trust configuration."""


class OIDCApprovalIdentityVerifier:
    """Callable identity_verifier for validate_dual_approval.

    assertion_resolver(context) must retrieve a server-side approval session
    and return {"id_token": str, "expected_nonce": str, "session_id": str}.
    It must not accept tokens, expected nonces, or session IDs supplied by the
    approval manifest.

    consume_assertion_session(session_id, expected_nonce) must atomically
    consume that server-side session exactly once. It must return True only
    for the first successful consumption; retries and concurrent replays
    must return False. This callback is mandatory and must use a shared,
    durable session store in production.

    signing_key_resolver(kid) must resolve a key from the configured issuer's
    authenticated JWKS source. role_resolver(issuer, subject, role) must query
    the current authoritative role assignment scoped to the exact issuer and
    subject on every call.
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        signing_key_resolver: Callable[[str], Any],
        assertion_resolver: Callable[[Mapping[str, Any]], Mapping[str, str]],
        consume_assertion_session: Callable[[str, str], bool],
        role_resolver: Callable[[str, str, str], bool],
        required_acr: str,
        required_amr: str = "webauthn",
        max_auth_age_seconds: int = 300,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (issuer, audience, required_acr, required_amr)):
            raise OIDCIdentityError("issuer, audience, ACR and AMR policy are required")
        parsed_issuer = urlsplit(issuer)
        if (
            parsed_issuer.scheme.lower() != "https"
            or not parsed_issuer.hostname
            or parsed_issuer.username is not None
            or parsed_issuer.password is not None
            or parsed_issuer.query
            or parsed_issuer.fragment
        ):
            raise OIDCIdentityError("issuer must be an HTTPS URL without credentials, query or fragment")
        if isinstance(max_auth_age_seconds, bool) or not isinstance(max_auth_age_seconds, int) or max_auth_age_seconds <= 0:
            raise OIDCIdentityError("max_auth_age_seconds must be a positive integer")
        self.issuer = issuer
        self.audience = audience
        self.signing_key_resolver = signing_key_resolver
        if not callable(consume_assertion_session):
            raise OIDCIdentityError("one-time assertion-session consumer is required")
        self.assertion_resolver = assertion_resolver
        self.consume_assertion_session = consume_assertion_session
        self.role_resolver = role_resolver
        self.required_acr = required_acr
        self.required_amr = required_amr
        self.max_auth_age_seconds = max_auth_age_seconds
        self.clock = clock

    def __call__(self, subject_id: str, role: str, context: Mapping[str, Any]) -> bool:
        if not isinstance(subject_id, str) or not subject_id:
            return False
        if not isinstance(role, str) or not role or not isinstance(context, Mapping):
            return False
        try:
            session = self.assertion_resolver(context)
            if not isinstance(session, Mapping):
                return False
            token = session.get("id_token")
            expected_nonce = session.get("expected_nonce")
            session_id = session.get("session_id")
            if (
                not isinstance(token, str) or not token
                or not isinstance(expected_nonce, str) or not expected_nonce
                or not isinstance(session_id, str) or not session_id.strip()
            ):
                return False

            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                return False
            kid = header.get("kid")
            if not isinstance(kid, str) or not kid:
                return False
            signing_key = self.signing_key_resolver(kid)
            if signing_key is None:
                return False

            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={
                    "require": ["exp", "iat", "sub", "iss", "aud", "nonce", "auth_time", "acr", "amr"],
                },
                leeway=5,
            )
            if claims.get("sub") != subject_id:
                return False
            # Require one exact relying-party audience. PyJWT otherwise accepts
            # the configured audience as one member of a multi-audience list.
            if claims.get("aud") != self.audience:
                return False
            token_nonce = claims.get("nonce")
            if not isinstance(token_nonce, str) or not hmac.compare_digest(token_nonce, expected_nonce):
                return False

            auth_time = claims.get("auth_time")
            if isinstance(auth_time, bool) or not isinstance(auth_time, (int, float)) or not math.isfinite(auth_time):
                return False
            age = self.clock() - auth_time
            if age < -5 or age > self.max_auth_age_seconds:
                return False
            if claims.get("acr") != self.required_acr:
                return False
            amr = claims.get("amr")
            if not isinstance(amr, list) or self.required_amr not in amr:
                return False

            # Re-check current role membership, then atomically consume the
            # server-side session. A valid ID token is not reusable evidence.
            if self.role_resolver(self.issuer, subject_id, role) is not True:
                return False
            return self.consume_assertion_session(session_id, expected_nonce) is True
        except (InvalidTokenError, OIDCIdentityError, KeyError, TypeError, ValueError):
            return False
        except Exception:
            # Trust-source outages and unexpected resolver errors fail closed.
            return False
