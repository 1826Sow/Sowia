import pytest

from final_tec_provider_contracts import (
    ProductionAdapterBundle,
    ProductionAdapterContractError,
    validate_production_adapter_bundle,
    validate_external_audit_anchor,
)


class Adapter:
    production_grade = True

    def resolve_signing_key(self, key_id): return object()
    def load_approval_session(self, context): return {}
    def consume_approval_session(self, session_id, expected_nonce): return True
    def has_current_role(self, subject_id, role): return True
    def sign(self, key_id, canonical_payload): return b"signature"
    def verify(self, key_id, canonical_payload, signature): return True
    def commit_pair_audit_and_outbox(self, authorization_id, nonce_records, audit_event): return object()
    def mark_checkpoint_anchored(self, authorization_id, event_hash, receipt): return True
    def pending_anchor_checkpoints(self): return []
    def healthcheck(self): return True
    def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc): return {"receipt_id": "test"}
    def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt): return True


def valid_bundle():
    adapters = [Adapter() for _ in range(7)]
    return ProductionAdapterBundle(*adapters)


def test_complete_declared_bundle_passes_structural_preflight():
    validate_production_adapter_bundle(valid_bundle())


def test_preflight_rejects_bundle_subclasses_without_running_overrides():
    calls = []

    class HostileBundle(ProductionAdapterBundle):
        @property
        def oidc_keys(self):
            calls.append("oidc_keys")
            raise RuntimeError("must not execute")

    valid = valid_bundle()
    hostile = object.__new__(HostileBundle)
    object.__setattr__(hostile, "sessions", valid.sessions)
    object.__setattr__(hostile, "roles", valid.roles)
    object.__setattr__(hostile, "signer", valid.signer)
    object.__setattr__(hostile, "signature_verifier", valid.signature_verifier)
    object.__setattr__(hostile, "ledger", valid.ledger)
    object.__setattr__(hostile, "audit_anchor", valid.audit_anchor)

    with pytest.raises(ProductionAdapterContractError, match="complete adapter bundle"):
        validate_production_adapter_bundle(hostile)

    assert calls == []


def test_missing_bundle_fails_closed():
    with pytest.raises(ProductionAdapterContractError):
        validate_production_adapter_bundle(None)


def test_adapter_without_production_declaration_fails_closed():
    bundle = valid_bundle()
    object.__setattr__(bundle.ledger, "production_grade", False)
    with pytest.raises(ProductionAdapterContractError, match="ledger"):
        validate_production_adapter_bundle(bundle)


def test_missing_atomic_outbox_ledger_contract_fails_closed():
    bundle = valid_bundle()

    class IncompleteLedger:
        production_grade = True

        def commit_pair_audit_and_outbox(self, authorization_id, nonce_records, audit_event):
            return object()

        def healthcheck(self):
            return True

    object.__setattr__(bundle, "ledger", IncompleteLedger())
    with pytest.raises(ProductionAdapterContractError, match="mark_checkpoint_anchored|pending_anchor_checkpoints"):
        validate_production_adapter_bundle(bundle)


def test_bundle_requires_all_seven_adapter_roles():
    with pytest.raises(TypeError):
        ProductionAdapterBundle(None, None, None, None, None, None)


def test_structural_preflight_never_calls_adapters_or_returns_authorization():
    class NoCallAdapter:
        production_grade = True

        def __init__(self):
            self.calls = []

        def _called(self, name):
            self.calls.append(name)
            raise AssertionError("Preflight must not invoke provider operations")

        def resolve_signing_key(self, *args): return self._called("resolve_signing_key")
        def load_approval_session(self, *args): return self._called("load_approval_session")
        def consume_approval_session(self, *args): return self._called("consume_approval_session")
        def has_current_role(self, *args): return self._called("has_current_role")
        def sign(self, *args): return self._called("sign")
        def verify(self, *args): return self._called("verify")
        def commit_pair_audit_and_outbox(self, *args): return self._called("commit_pair_audit_and_outbox")
        def mark_checkpoint_anchored(self, *args): return self._called("mark_checkpoint_anchored")
        def pending_anchor_checkpoints(self, *args): return self._called("pending_anchor_checkpoints")
        def healthcheck(self, *args): return self._called("healthcheck")
        def append_checkpoint(self, *args): return self._called("append_checkpoint")
        def verify_checkpoint(self, *args): return self._called("verify_checkpoint")

    adapters = [NoCallAdapter() for _ in range(7)]
    bundle = ProductionAdapterBundle(*adapters)

    result = validate_production_adapter_bundle(bundle)

    assert all(adapter.calls == [] for adapter in adapters)
    assert result is None
    assert not hasattr(result, "execution_authorized")
    assert not hasattr(result, "g2b_status")


def test_preflight_does_not_execute_adapter_properties_or_descriptors():
    calls = []

    class HostileAdapter(Adapter):
        @property
        def production_grade(self):
            calls.append("production_grade")
            raise RuntimeError("must not execute")

        @property
        def healthcheck(self):
            calls.append("healthcheck")
            raise RuntimeError("must not execute")

    adapters = [HostileAdapter(), *[Adapter() for _ in range(6)]]
    bundle = ProductionAdapterBundle(*adapters)

    with pytest.raises(ProductionAdapterContractError, match="oidc_keys|ledger"):
        validate_production_adapter_bundle(bundle)

    assert calls == []


class AuditAnchor:
    production_grade = True

    def append_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc):
        raise AssertionError("Structural validation must not call the anchor")

    def verify_checkpoint(self, sequence, previous_hash, event_hash, created_at_utc, receipt):
        raise AssertionError("Structural validation must not call the anchor")


def test_external_audit_anchor_contract_passes_static_preflight():
    assert validate_external_audit_anchor(AuditAnchor()) is None


def test_external_audit_anchor_missing_or_incomplete_fails_closed():
    with pytest.raises(ProductionAdapterContractError):
        validate_external_audit_anchor(None)

    class IncompleteAnchor:
        production_grade = True

        def append_checkpoint(self, *args):
            return {}

    with pytest.raises(ProductionAdapterContractError, match="verify_checkpoint"):
        validate_external_audit_anchor(IncompleteAnchor())


def test_external_audit_anchor_preflight_does_not_execute_properties():
    calls = []

    class HostileAnchor(AuditAnchor):
        @property
        def production_grade(self):
            calls.append("production_grade")
            raise RuntimeError("must not execute")

    with pytest.raises(ProductionAdapterContractError):
        validate_external_audit_anchor(HostileAnchor())
    assert calls == []



def test_session_adapter_requires_atomic_one_time_consumption():
    bundle = valid_bundle()

    class IncompleteSessionStore:
        production_grade = True

        def load_approval_session(self, context):
            return {}

    object.__setattr__(bundle, "sessions", IncompleteSessionStore())
    with pytest.raises(ProductionAdapterContractError, match="consume_approval_session"):
        validate_production_adapter_bundle(bundle)
