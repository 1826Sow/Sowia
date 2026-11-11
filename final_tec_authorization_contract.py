"""Offline structural gate for the FINAL TEC G0–G2-B authorization contract.

This module validates a contract and delegates trust decisions to injected
verifier/identity/nonce callbacks. It does not implement cryptography, durable
nonce storage, host attestation, or workload execution. Test callbacks are fakes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import base64
import binascii
import math
import re
from typing import Any, Callable, Mapping


class AuthorizationContractError(ValueError):
    """Raised when the proposed authorization contract fails closed."""


_HEX_64 = re.compile(r"^[a-f0-9]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{1,119}$")
_REQUIRED_TOP = {
    "schema_version", "authorization_id", "run_id", "nonce", "issued_at",
    "expires_at", "revoked_at", "status", "scenario_id", "actors",
    "approval", "environment", "constraints",
}
_ACTORS = {"requester_id", "approver_id", "operator_id", "reviewer_id"}
_APPROVAL = {"approver_role", "approval_policy_id", "algorithm", "key_id", "signature"}
_ENVIRONMENT = {
    "host_id", "host_os", "kernel_version", "architecture", "runtime_name",
    "runtime_version", "runtime_config_digest", "image_digest",
    "g2a_profile_digest", "workload_digest",
}
_CONSTRAINTS = {
    "network_policy", "secrets_policy", "cpu_limit", "memory_limit_bytes",
    "pids_limit", "io_limit_bytes", "scratch_limit_bytes", "output_limit_bytes",
    "timeout_seconds", "budget_limit", "currency", "stop_controller_id",
    "stop_policy_version",
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or not _ID.fullmatch(value):
        raise AuthorizationContractError(f"{field}: identifiant/texte invalide.")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise AuthorizationContractError(f"{field}: horodatage obligatoire.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorizationContractError(f"{field}: date ISO 8601 invalide.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuthorizationContractError(f"{field}: fuseau horaire obligatoire.")
    return parsed.astimezone(timezone.utc)


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AuthorizationContractError(f"{field}: entier invalide.")
    if value < 0 or (value == 0 and not allow_zero):
        raise AuthorizationContractError(f"{field}: valeur hors limites.")
    return value


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise AuthorizationContractError(f"{field}: digest SHA-256 attendu.")
    return value


def validate_authorization_contract(
    contract: Mapping[str, Any],
    *,
    expected_environment: Mapping[str, str],
    signature_verifier: Callable[[Mapping[str, Any], Mapping[str, Any]], bool],
    identity_verifier: Callable[[str, str], bool],
    nonce_consumer: Callable[[str, str], bool],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate the contract and consume its nonce through a trusted callback.

    Callback contracts:
    - signature_verifier(payload_without_approval_signature, approval) verifies
      the actual signature against a trusted key registry.
    - identity_verifier(approver_id, approver_role) checks authoritative identity
      and role assignment.
    - nonce_consumer(nonce, authorization_id) atomically consumes a durable,
      single-use nonce. It must return False for unknown, expired, revoked,
      previously consumed, or concurrently consumed nonces.

    This function never launches or authorizes a workload by itself. The returned
    status is only contract validation; host controls require independent evidence.
    """
    if not isinstance(contract, Mapping):
        raise AuthorizationContractError("Le contrat doit être un objet.")
    if set(contract) != _REQUIRED_TOP:
        missing = sorted(_REQUIRED_TOP - set(contract))
        unknown = sorted(set(contract) - _REQUIRED_TOP)
        raise AuthorizationContractError(f"Champs invalides; absents={missing}; inconnus={unknown}.")

    if contract["schema_version"] != "1.0":
        raise AuthorizationContractError("Version de schéma non prise en charge.")
    authorization_id = _text(contract["authorization_id"], "authorization_id")
    run_id = _text(contract["run_id"], "run_id")
    nonce = contract["nonce"]
    if not isinstance(nonce, str) or len(nonce) < 32 or len(nonce) > 256:
        raise AuthorizationContractError("nonce: valeur aléatoire opaque de 32 à 256 caractères requise.")
    _text(contract["scenario_id"], "scenario_id")
    if contract["status"] != "approved":
        raise AuthorizationContractError("L'autorisation doit être approuvée.")

    issued = _timestamp(contract["issued_at"], "issued_at")
    expires = _timestamp(contract["expires_at"], "expires_at")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise AuthorizationContractError("L'horloge doit inclure un fuseau horaire.")
    current = current.astimezone(timezone.utc)
    if issued > current or expires <= current or expires <= issued:
        raise AuthorizationContractError("Fenêtre de validité absente, future ou expirée.")
    if contract["revoked_at"] is not None:
        revoked = _timestamp(contract["revoked_at"], "revoked_at")
        if revoked <= current:
            raise AuthorizationContractError("Autorisation révoquée.")

    actors = contract["actors"]
    if not isinstance(actors, Mapping) or set(actors) != _ACTORS:
        raise AuthorizationContractError("Bloc actors incomplet ou contenant des champs inconnus.")
    for key, value in actors.items():
        _text(value, f"actors.{key}")
    if actors["requester_id"] == actors["approver_id"]:
        raise AuthorizationContractError("Auto-approbation interdite.")
    if actors["operator_id"] == actors["reviewer_id"]:
        raise AuthorizationContractError("L'opérateur et le réviseur doivent être distincts.")
    if actors["approver_id"] == actors["reviewer_id"]:
        raise AuthorizationContractError("L'approbateur et le réviseur doivent être distincts.")

    approval = contract["approval"]
    if not isinstance(approval, Mapping) or set(approval) != _APPROVAL:
        raise AuthorizationContractError("Bloc approval incomplet ou contenant des champs inconnus.")
    approver_role = _text(approval["approver_role"], "approval.approver_role")
    _text(approval["approval_policy_id"], "approval.approval_policy_id")
    key_id = _text(approval["key_id"], "approval.key_id")
    if approval["algorithm"] != "Ed25519":
        raise AuthorizationContractError("Algorithme de signature non autorisé.")
    signature = approval["signature"]
    if not isinstance(signature, str) or len(signature) > 256:
        raise AuthorizationContractError("Signature encodée absente ou de longueur invalide.")
    try:
        decoded_signature = base64.b64decode(signature, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise AuthorizationContractError("Signature : encodage Base64 invalide.") from exc
    if len(decoded_signature) != 64:
        raise AuthorizationContractError("Signature Ed25519 : 64 octets attendus.")

    environment = contract["environment"]
    if not isinstance(environment, Mapping) or set(environment) != _ENVIRONMENT:
        raise AuthorizationContractError("Bloc environment incomplet ou contenant des champs inconnus.")
    for key, value in environment.items():
        _text(value, f"environment.{key}")
    for key in ("runtime_config_digest", "image_digest", "g2a_profile_digest", "workload_digest"):
        _digest(environment[key], f"environment.{key}")
    if not isinstance(expected_environment, Mapping) or set(expected_environment) != _ENVIRONMENT:
        raise AuthorizationContractError("Contexte environnemental attendu incomplet.")
    if dict(environment) != dict(expected_environment):
        raise AuthorizationContractError("L'environnement observé ne correspond pas à l'environnement signé.")

    constraints = contract["constraints"]
    if not isinstance(constraints, Mapping) or set(constraints) != _CONSTRAINTS:
        raise AuthorizationContractError("Bloc constraints incomplet ou contenant des champs inconnus.")
    if constraints["network_policy"] != "deny_all" or constraints["secrets_policy"] != "none":
        raise AuthorizationContractError("G2-B initial exige réseau deny_all et aucun secret.")
    for field in (
        "memory_limit_bytes", "pids_limit", "io_limit_bytes", "scratch_limit_bytes",
        "output_limit_bytes", "timeout_seconds",
    ):
        _positive_int(constraints[field], f"constraints.{field}")
    cpu = constraints["cpu_limit"]
    if isinstance(cpu, bool) or not isinstance(cpu, (int, float)) or not math.isfinite(float(cpu)) or cpu <= 0 or cpu > 64:
        raise AuthorizationContractError("constraints.cpu_limit hors limites.")
    if constraints["budget_limit"] != 0:
        raise AuthorizationContractError("Le smoke test local initial doit avoir un budget nul.")
    if constraints["currency"] != "EUR":
        raise AuthorizationContractError("Devise de référence attendue : EUR.")
    _text(constraints["stop_controller_id"], "constraints.stop_controller_id")
    _text(constraints["stop_policy_version"], "constraints.stop_policy_version")

    # Verify trusted identities and signature before consuming the one-time nonce.
    if identity_verifier(actors["approver_id"], approver_role) is not True:
        raise AuthorizationContractError("Identité ou rôle de l'approbateur non vérifié.")
    signed_approval = {key: value for key, value in approval.items() if key != "signature"}
    payload = {key: value for key, value in contract.items() if key != "approval"}
    payload["approval"] = signed_approval
    if signature_verifier(payload, approval) is not True:
        raise AuthorizationContractError("Signature invalide ou clé non approuvée.")
    if nonce_consumer(nonce, authorization_id) is not True:
        raise AuthorizationContractError("Nonce inconnu, expiré, révoqué ou déjà consommé.")

    return {
        "authorization_id": authorization_id,
        "run_id": run_id,
        "contract_result": "contract_validated_not_execution_authorized",
        "signature_verified_by_injected_verifier": True,
        "identity_verified_by_injected_verifier": True,
        "nonce_consumed_by_injected_store": True,
        "host_controls_verified": False,
        "workload_executed": False,
        "evidence_status": "pending",
        "publication_state": "draft",
    }
