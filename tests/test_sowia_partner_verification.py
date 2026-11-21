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



def test_server_dns_resolver_uses_fixed_endpoint_and_returns_txt(monkeypatch):
    from types import SimpleNamespace
    import requests
    from sowia_partner_verification import resolve_domain_challenge_txt

    captured = {}
    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "Status": 0,
                "Answer": [
                    {"name": "_sowia-verification.example.com.", "type": 16,
                     "TTL": 60, "data": '"sowia-verification=abc123"'}
                ],
            },
        )
    monkeypatch.setattr(requests, "get", fake_get)
    assert resolve_domain_challenge_txt("example.com") == ["sowia-verification=abc123"]
    assert captured["url"] == "https://cloudflare-dns.com/dns-query"
    assert captured["params"] == {"name": "_sowia-verification.example.com", "type": "TXT"}
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == (3.0, 5.0)


def test_server_dns_resolver_rejects_invalid_timeout_and_dns_status(monkeypatch):
    from types import SimpleNamespace
    import requests
    from sowia_partner_verification import (
        PartnerVerificationError, resolve_domain_challenge_txt,
    )
    with pytest.raises(PartnerVerificationError):
        resolve_domain_challenge_txt("example.com", timeout=30)

    monkeypatch.setattr(
        requests, "get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"Status": 3, "Answer": []}
        ),
    )
    with pytest.raises(PartnerVerificationError):
        resolve_domain_challenge_txt("example.com")


def test_dns_confirmation_uses_server_resolver_and_still_binds_owner(monkeypatch):
    import sowia_partner_verification as verification
    challenge = issue_domain_challenge(owner_id="user-1", domain="example.com", now=NOW)
    record = domain_challenge_dns_record(challenge)["value"]
    monkeypatch.setattr(verification, "resolve_domain_challenge_txt", lambda domain: [record])
    proof = verification.confirm_domain_control_via_dns(
        challenge, authenticated_owner_id="user-1", checked_at=NOW + timedelta(minutes=1)
    )
    assert proof["verified"] is True
    with pytest.raises(PartnerVerificationError):
        verification.confirm_domain_control_via_dns(
            challenge, authenticated_owner_id="user-2", checked_at=NOW + timedelta(minutes=1)
        )

def test_server_dns_resolver_ignores_txt_records_for_other_names(monkeypatch):
    from types import SimpleNamespace
    import requests
    from sowia_partner_verification import resolve_domain_challenge_txt

    monkeypatch.setattr(
        requests, "get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "Status": 0,
                "Answer": [
                    {"name": "_other.example.com.", "type": 16,
                     "data": '"sowia-verification=attacker-value"'},
                    {"name": "_sowia-verification.example.com.", "type": 16,
                     "data": '"sowia-verification=correct-value"'},
                ],
            },
        ),
    )
    assert resolve_domain_challenge_txt("example.com") == [
        "sowia-verification=correct-value"
    ]
