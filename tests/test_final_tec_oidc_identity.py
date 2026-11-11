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
                   consume_assertion_session=None, clock=time.time):
    return OIDCApprovalIdentityVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        signing_key_resolver=key_resolver or (lambda kid: public if kid == "issuer-key-1" else None),
        assertion_resolver=assertion_resolver or (
            lambda context: {
                "id_token": token,
                "expected_nonce": expected_nonce,
                "session_id": "server-session-001",
            }
        ),
        consume_assertion_session=consume_assertion_session or (lambda session_id, nonce: True),
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


def test_multi_audience_token_is_rejected_even_when_expected_audience_is_present(signing_material):
    private, public = signing_material
    verifier = build_verifier(
        make_token(private, aud=[AUDIENCE, "another-client"]), public
    )
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


def test_oauth_only_amr_is_rejected_for_final_tec_approval(signing_material):
    private, public = signing_material
    verifier = build_verifier(make_token(private, amr=["oauth"]), public)
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
            consume_assertion_session=lambda session_id, nonce: True,
            role_resolver=lambda subject, role: False,
            required_acr="acr",
        )


@pytest.mark.parametrize("issuer", [
    "http://identity.example.test/",
    "https:///missing-host",
    "https://user:password@identity.example.test/",
    "https://identity.example.test/?tenant=unexpected",
    "https://identity.example.test/#fragment",
])
def test_insecure_or_ambiguous_issuer_configuration_is_rejected(issuer):
    with pytest.raises(OIDCIdentityError):
        OIDCApprovalIdentityVerifier(
            issuer=issuer,
            audience=AUDIENCE,
            signing_key_resolver=lambda kid: None,
            assertion_resolver=lambda context: {},
            consume_assertion_session=lambda session_id, nonce: True,
            role_resolver=lambda subject, role: False,
            required_acr="acr",
        )


def test_boolean_auth_age_configuration_is_rejected():
    with pytest.raises(OIDCIdentityError):
        OIDCApprovalIdentityVerifier(
            issuer=ISSUER,
            audience=AUDIENCE,
            signing_key_resolver=lambda kid: None,
            assertion_resolver=lambda context: {},
            consume_assertion_session=lambda session_id, nonce: True,
            role_resolver=lambda subject, role: False,
            required_acr="acr",
            max_auth_age_seconds=True,
        )


def test_oidc_verifier_integrates_with_dual_approval_engine(signing_material):
    from datetime import timedelta
    from final_tec_dual_approval import validate_dual_approval

    now_dt = datetime.now(timezone.utc)
    now = int(now_dt.timestamp())
    private_a, public_a = signing_material
    tokens = {
        "key-a": make_token(private_a, sub="approver-a", nonce="nonce-a"),
        "key-b": make_token(private_a, sub="approver-b", nonce="nonce-b"),
    }
    keys = {"issuer-key-1": public_a}
    nonces = {"key-a": "nonce-a", "key-b": "nonce-b"}
    consumed_sessions = set()
    verifier = OIDCApprovalIdentityVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        signing_key_resolver=lambda kid: keys.get(kid),
        assertion_resolver=lambda context: {
            "id_token": tokens[context["approval"]["key_id"]],
            "expected_nonce": nonces[context["approval"]["key_id"]],
            "session_id": "server-session-" + context["approval"]["key_id"],
        },
        consume_assertion_session=lambda session_id, nonce: session_id not in consumed_sessions
            and not consumed_sessions.add(session_id),
        role_resolver=lambda subject, role: (
            subject in {"approver-a", "approver-b"} and role == "security-approver"
        ),
        required_acr="urn:example:loa:phishing-resistant",
        required_amr="webauthn",
    )
    request = {
        "authorization_id": "oidc-engine-auth",
        "request_version": "v1",
        "requester_id": "requester",
        "operator_id": "operator",
        "reviewer_id": "reviewer",
        "policy_version": "policy-v1",
        "expires_at": (now_dt + timedelta(minutes=5)).isoformat(),
        "environment_digest": "a" * 64,
        "constraints_digest": "b" * 64,
        "action_digest": "c" * 64,
    }
    approvals = []
    for index, subject in enumerate(("approver-a", "approver-b")):
        key_id = "key-a" if index == 0 else "key-b"
        nonce = nonces[key_id]
        approvals.append({
            "subject_id": subject,
            "role": "security-approver",
            "key_id": key_id,
            "algorithm": "Ed25519",
            "approval_policy_id": "dual-v1",
            "policy_version": "policy-v1",
            "nonce": nonce + ("x" * 40),
            "issued_at": (now_dt - timedelta(seconds=1)).isoformat(),
            "expires_at": (now_dt + timedelta(minutes=2)).isoformat(),
            "signature": "signature-placeholder",
        })
    result = validate_dual_approval(
        request,
        approvals,
        signature_verifier=lambda envelope, approval: True,
        identity_verifier=verifier,
        atomic_pair_audit_commit=lambda authorization_id, records, event: True,
        now=now_dt,
    )
    assert result["identities_verified_by_injected_authority"] is True
    assert result["execution_authorized"] is False
    assert result["workload_executed"] is False
