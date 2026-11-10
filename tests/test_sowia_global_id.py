import pytest

from sowia_global_id import (
    GlobalIDError,
    create_public_id,
    profile_completeness,
    public_profile,
    qr_payload,
    set_verification_status,
)


def test_public_id_is_stable_and_does_not_expose_source_uuid():
    source = "ef346b19-9dd6-49a0-941d-449f48c77891"
    first = create_public_id(source)
    assert first == create_public_id(source)
    assert first.startswith("SOWIA-")
    assert source not in first


def test_public_id_requires_persistent_uuid():
    with pytest.raises(GlobalIDError):
        create_public_id("user@example.com")


def test_public_profile_uses_allowlist_and_hides_private_fields():
    profile = public_profile({
        "public_id": "SOWIA-ABCDEF0123456789ABCD",
        "display_name": "Sowkeys",
        "email": "private@example.com",
        "user_id": "private-user-id",
        "phone": "+33000000000",
        "verification_status": "verified",
    })
    assert profile["display_name"] == "Sowkeys"
    assert profile["verification_status"] == "verified"
    assert "email" not in profile
    assert "user_id" not in profile
    assert "phone" not in profile


def test_profile_completeness_is_explainable():
    result = profile_completeness({
        "display_name": "Sowkeys",
        "app_name": "SOWIA",
        "country": "France",
        "languages": ["fr", "en"],
    })
    assert result["completed"] == 4
    assert result["total"] == 6
    assert result["percent"] == 67


def test_only_admin_can_verify_and_evidence_is_required():
    row = {"public_id": "SOWIA-ABCDEF0123456789ABCD"}
    with pytest.raises(GlobalIDError):
        set_verification_status(row, "verified", actor_role="member",
                                evidence_reference="case-1")
    with pytest.raises(GlobalIDError):
        set_verification_status(row, "verified", actor_role="admin")
    verified = set_verification_status(
        row, "verified", actor_role="admin", evidence_reference="case-1"
    )
    assert verified["verification_status"] == "verified"
    assert verified["verification_evidence_reference"] == "case-1"


def test_qr_payload_is_https_profile_url():
    result = qr_payload(
        "SOWIA-ABCDEF0123456789ABCD",
        base_url="https://sowia.example",
    )
    assert result == "https://sowia.example/id/SOWIA-ABCDEF0123456789ABCD"
    with pytest.raises(GlobalIDError):
        qr_payload("SOWIA-ABC", base_url="http://sowia.example")
