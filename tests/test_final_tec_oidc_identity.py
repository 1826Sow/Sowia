from datetime import datetime, timezone
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from final_tec_oidc_identity import OIDCApprovalIdentityVerifier, OIDCIdentityError


ISSUER = "https://identity.example.test/"
AUDIENCE = "final-tec-approvals"
SUBJECT = "approver-001"
NONCE = "session-nonce-unique-001"


@pytest.fixture
def signing_material():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()
    return private, public


def make_token(private, **overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": SUBJECT,
        "iat": now,
        "exp": now + 120,
        "auth_time": now - 10,
        "nonce": NONCE,
        "acr": "urn:example:loa:phishing-resistant",
        "amr": ["webauthn"],
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "issuer-key-1"})


def build_verifier(token, public, *, role_ok=True, expected_nonce=NONCE,
                   key_resolver=None, role_resolver=None, assertion_resolver=None,
                   clock=time.time):
    return OIDCApprovalIdentityVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        signing_key_resolver=key_resolver or (lambda kid: public if kid == "issuer-key-1" else None),
        assertion_resolver=assertion_resolver or (
            lambda context: {"id_token": token, "expected_nonce": expected_nonce}
        ),
        role_resolver=role_resolver or (lambda subject, role: role_ok and role == "security-approver"),
        required_acr="urn:example:loa:phishing-resistant",
        required_amr="webauthn",
        max_auth_age_seconds=300,
        clock=clock,
    )


def test_valid_oidc_identity_and_current_role_are_accepted(signing_material):
    private, public = signing_material
    token = make_token(private)
    verifier = build_verifier(token, public)
    assert verifier(SUBJECT, "security-approver", {"approval": {"key_id": "k1"}}) is True


def test_wrong_subject_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private), public)
    assert verifier("different-subject", "security-approver", {}) is False


def test_wrong_issuer_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private, iss="https://attacker.example/"), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_wrong_audience_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private, aud="other-service"), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_expired_token_is_rejected(signing_material):
    private, public = signing_material
    now = int(time.time())
    verifier = build_verifier(make_token(private, exp=now - 60, iat=now - 120), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_wrong_session_nonce_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private), public, expected_nonce="different-session")
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_stale_authentication_is_rejected(signing_material):
    private, public = signing_material
    now = int(time.time())
    verifier = build_verifier(make_token(private, auth_time=now - 900), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_missing_phishing_resistant_amr_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private, amr=["pwd", "otp"]), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_wrong_acr_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private, acr="urn:example:loa:basic"), public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_unknown_jwks_key_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private), public, key_resolver=lambda kid: None)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_role_is_rechecked_and_missing_role_is_rejected(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private), public, role_ok=False)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_session_resolver_failure_fails_closed(signing_material):
    private, public = signing_material
    verifier = build_verifier(
        make_token(private), public,
        assertion_resolver=lambda context: (_ for _ in ()).throw(RuntimeError("session store offline")),
    )
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_token_without_required_claims_is_rejected(signing_material):
    private, public = signing_material
    now = int(time.time())
    claims = {
        "iss": ISSUER, "aud": AUDIENCE, "sub": SUBJECT,
        "iat": now, "exp": now + 120,
    }
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "issuer-key-1"})
    verifier = build_verifier(token, public)
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_unsigned_none_algorithm_is_rejected():
    token = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": SUBJECT},
        key="",
        algorithm="none",
        headers={"kid": "issuer-key-1"},
    )
    verifier = build_verifier(token, object())
    assert verifier(SUBJECT, "security-approver", {}) is False


def test_invalid_configuration_is_rejected():
    with pytest.raises(OIDCIdentityError):
        OIDCApprovalIdentityVerifier(
            issuer="", audience=AUDIENCE,
            signing_key_resolver=lambda kid: None,
            assertion_resolver=lambda context: {},
            role_resolver=lambda subject, role: False,
            required_acr="acr",
        )
