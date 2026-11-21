from datetime import datetime, timedelta, timezone

import pytest

from sowia_partner_verification import (
    PartnerVerificationError,
    confirm_domain_control_from_dns,
    domain_challenge_dns_record,
    issue_domain_challenge,
    normalize_partner_domain,
)


NOW = datetime(2026, 11, 21, 18, 0, tzinfo=timezone.utc)


def test_normalize_domain_accepts_https_origin_and_idn():
    assert normalize_partner_domain("https://Example.COM/") == "example.com"
    assert normalize_partner_domain("münich.example") == "xn--mnich-kva.example"


@pytest.mark.parametrize("value", [
    "", "http://example.com", "https://user@example.com",
    "https://example.com:8443", "https://example.com:abc", "https://example.com:", "https://example.com/path",
    "example.com/path", "127.0.0.1", "localhost", "bad..example",
])
def test_normalize_domain_rejects_unsafe_or_non_origin_inputs(value):
    with pytest.raises(PartnerVerificationError):
        normalize_partner_domain(value)


def test_issue_domain_challenge_creates_random_expiring_txt_proof():
    first = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    second = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    record = domain_challenge_dns_record(first)
    assert first.token != second.token
    assert len(first.token) >= 40
    assert record["host"] == "_sowia-verification.example.com"
    assert record["type"] == "TXT"
    assert record["value"] == f"sowia-verification={first.token}"
    assert first.expires_at == NOW + timedelta(hours=24)


def test_issue_domain_challenge_requires_owner_aware_time_and_bounded_ttl():
    with pytest.raises(PartnerVerificationError):
        issue_domain_challenge(owner_id="", domain="example.com", now=NOW)
    with pytest.raises(PartnerVerificationError):
        issue_domain_challenge(owner_id="user-1", domain="example.com", now=datetime(2026, 11, 21))
    with pytest.raises(PartnerVerificationError):
        issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW, ttl=timedelta(days=3))


def test_confirm_domain_control_requires_exact_dns_txt_and_owner():
    challenge = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    txt = domain_challenge_dns_record(challenge)["value"]
    proof = confirm_domain_control_from_dns(
        challenge, authenticated_owner_id="user-1",
        dns_txt_records=[txt], checked_at=NOW + timedelta(minutes=2),
    )
    assert proof["verified"] is True
    assert proof["verification_method"] == "dns_txt"
    assert proof["domain"] == "example.com"
    assert proof["owner_id"] == "user-1"
    assert "token" not in proof


@pytest.mark.parametrize("kwargs", [
    {"authenticated_owner_id": "user-2", "dns_txt_records": ["sowia-verification=wrong"]},
    {"authenticated_owner_id": "user-1", "dns_txt_records": ["sowia-verification=wrong"]},
    {"authenticated_owner_id": "user-1", "dns_txt_records": "sowia-verification=wrong"},
])
def test_confirm_domain_control_rejects_wrong_owner_or_untrusted_shape(kwargs):
    challenge = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    with pytest.raises(PartnerVerificationError):
        confirm_domain_control_from_dns(
            challenge, checked_at=NOW + timedelta(minutes=1), **kwargs
        )


def test_confirm_domain_control_rejects_expired_or_replayed_challenge():
    challenge = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    txt = [domain_challenge_dns_record(challenge)["value"]]
    with pytest.raises(PartnerVerificationError, match="expiré"):
        confirm_domain_control_from_dns(
            challenge, authenticated_owner_id="user-1", dns_txt_records=txt,
            checked_at=challenge.expires_at,
        )
    with pytest.raises(PartnerVerificationError, match="déjà été utilisé"):
        confirm_domain_control_from_dns(
            challenge, authenticated_owner_id="user-1", dns_txt_records=txt,
            checked_at=NOW + timedelta(minutes=1), consumed_at=NOW,
        )
