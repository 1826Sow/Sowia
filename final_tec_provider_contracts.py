"""Provider-neutral production adapter contracts for FINAL TEC.

These Protocols define integration seams only. They do not implement network
clients, establish provider trust, or certify an adapter as production-ready.
A production marker is a configuration assertion, never independent evidence.
"""
from __future__ import annotations

import inspect
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
    """Shared ledger must atomically persist pair, audit, and anchor outbox."""

    production_grade: bool

    def commit_pair_audit_and_outbox(
        self,
        authorization_id: str,
        nonce_records: Sequence[tuple[str, str]],
        audit_event: Mapping[str, Any],
    ) -> Any: ...

    def mark_checkpoint_anchored(
        self,
        authorization_id: str,
        event_hash: str,
        receipt: Mapping[str, str],
    ) -> bool: ...

    def pending_anchor_checkpoints(self) -> Sequence[Any]: ...

    def healthcheck(self) -> bool: ...


@runtime_checkable
class ExternalAuditAnchor(Protocol):
    """Independent external checkpoint anchor; interface only, no provider."""

    production_grade: bool

    def append_checkpoint(
        self, sequence: int, previous_hash: str, event_hash: str, created_at_utc: str
    ) -> Mapping[str, str]: ...

    def verify_checkpoint(
        self, sequence: int, previous_hash: str, event_hash: str,
        created_at_utc: str, receipt: Mapping[str, str]
    ) -> bool: ...


@dataclass(frozen=True)
class ProductionAdapterBundle:
    oidc_keys: OIDCKeySource
    sessions: ApprovalSessionStore
    roles: CurrentRoleDirectory
    signer: RemoteApprovalSigner
    signature_verifier: RemoteApprovalSignatureVerifier
    ledger: SharedAtomicApprovalLedger
    audit_anchor: ExternalAuditAnchor


_REQUIRED_METHODS = {
    "oidc_keys": ("resolve_signing_key",),
    "sessions": ("load_approval_session",),
    "roles": ("has_current_role",),
    "signer": ("sign",),
    "signature_verifier": ("verify",),
    "ledger": (
        "commit_pair_audit_and_outbox",
        "mark_checkpoint_anchored",
        "pending_anchor_checkpoints",
        "healthcheck",
    ),
    "audit_anchor": ("append_checkpoint", "verify_checkpoint"),
}
_MISSING = object()


class ProductionAdapterContractError(ValueError):
    """Raised when a required production adapter is absent or incomplete."""


def _static_attribute(instance: object, name: str) -> Any:
    """Inspect an attribute without executing descriptors or properties."""
    try:
        return inspect.getattr_static(instance, name)
    except AttributeError:
        return _MISSING


def validate_external_audit_anchor(anchor: ExternalAuditAnchor) -> None:
    """Static structural preflight only; never contacts or certifies an anchor."""
    if anchor is None:
        raise ProductionAdapterContractError("An external audit anchor is required")
    failures: list[str] = []
    if _static_attribute(anchor, "production_grade") is not True:
        failures.append("audit_anchor: production_grade must be explicitly true")
    for method in ("append_checkpoint", "verify_checkpoint"):
        candidate = _static_attribute(anchor, method)
        if candidate is _MISSING or not callable(candidate):
            failures.append(f"audit_anchor: missing callable {method}")
    if failures:
        raise ProductionAdapterContractError("; ".join(failures))


def validate_production_adapter_bundle(bundle: ProductionAdapterBundle) -> None:
    """Check structural completeness without executing adapter-controlled code.

    This is only a local preflight. It does not contact providers, verify their
    security posture, or replace integration tests and independent review.
    Attribute inspection is static so hostile properties/descriptors cannot
    run code during this check.
    """
    if type(bundle) is not ProductionAdapterBundle:
        raise ProductionAdapterContractError("A complete adapter bundle is required")

    failures: list[str] = []
    for field, methods in _REQUIRED_METHODS.items():
        adapter = getattr(bundle, field, None)
        if adapter is None:
            failures.append(f"{field}: missing")
            continue

        production_marker = _static_attribute(adapter, "production_grade")
        if production_marker is not True:
            failures.append(f"{field}: production_grade must be explicitly true")

        for method in methods:
            candidate = _static_attribute(adapter, method)
            if candidate is _MISSING or not callable(candidate):
                failures.append(f"{field}: missing callable {method}")

    if failures:
        raise ProductionAdapterContractError("; ".join(failures))
