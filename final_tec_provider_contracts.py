"""Provider-neutral production adapter contracts for FINAL TEC.

These Protocols define integration seams only. They do not implement network
clients, establish provider trust, or certify an adapter as production-ready.
A production marker is a configuration assertion, never independent evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class OIDCKeySource(Protocol):
    production_grade: bool

    def resolve_signing_key(self, key_id: str) -> Any: ...


@runtime_checkable
class ApprovalSessionStore(Protocol):
    production_grade: bool

    def load_approval_session(self, context: Mapping[str, Any]) -> Mapping[str, str]: ...


@runtime_checkable
class CurrentRoleDirectory(Protocol):
    production_grade: bool

    def has_current_role(self, subject_id: str, role: str) -> bool: ...


@runtime_checkable
class RemoteApprovalSigner(Protocol):
    production_grade: bool

    def sign(self, key_id: str, canonical_payload: bytes) -> bytes: ...


@runtime_checkable
class RemoteApprovalSignatureVerifier(Protocol):
    production_grade: bool

    def verify(self, key_id: str, canonical_payload: bytes, signature: bytes) -> bool: ...


@runtime_checkable
class SharedAtomicApprovalLedger(Protocol):
    production_grade: bool

    def commit_pair_and_audit(
        self,
        authorization_id: str,
        nonce_records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
    ) -> bool: ...

    def healthcheck(self) -> bool: ...


@dataclass(frozen=True)
class ProductionAdapterBundle:
    oidc_keys: OIDCKeySource
    sessions: ApprovalSessionStore
    roles: CurrentRoleDirectory
    signer: RemoteApprovalSigner
    signature_verifier: RemoteApprovalSignatureVerifier
    ledger: SharedAtomicApprovalLedger


_REQUIRED_METHODS = {
    "oidc_keys": ("resolve_signing_key",),
    "sessions": ("load_approval_session",),
    "roles": ("has_current_role",),
    "signer": ("sign",),
    "signature_verifier": ("verify",),
    "ledger": ("commit_pair_and_audit", "healthcheck"),
}


class ProductionAdapterContractError(ValueError):
    """Raised when a required production adapter is absent or incomplete."""


def validate_production_adapter_bundle(bundle: ProductionAdapterBundle) -> None:
    """Check structural completeness and explicit production declarations.

    This is only a local preflight. It does not contact providers, verify their
    security posture, or replace integration tests and independent review.
    """
    if not isinstance(bundle, ProductionAdapterBundle):
        raise ProductionAdapterContractError("A complete adapter bundle is required")

    failures: list[str] = []
    for field, methods in _REQUIRED_METHODS.items():
        adapter = getattr(bundle, field, None)
        if adapter is None:
            failures.append(f"{field}: missing")
            continue
        if getattr(adapter, "production_grade", False) is not True:
            failures.append(f"{field}: production_grade must be explicitly true")
        for method in methods:
            if not callable(getattr(adapter, method, None)):
                failures.append(f"{field}: missing callable {method}")

    if failures:
        raise ProductionAdapterContractError("; ".join(failures))
