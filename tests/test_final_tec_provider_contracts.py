import pytest

from final_tec_provider_contracts import (
    ProductionAdapterBundle,
    ProductionAdapterContractError,
    validate_production_adapter_bundle,
)


class Adapter:
    production_grade = True

    def resolve_signing_key(self, key_id): return object()
    def load_approval_session(self, context): return {}
    def has_current_role(self, subject_id, role): return True
    def sign(self, key_id, canonical_payload): return b"signature"
    def verify(self, key_id, canonical_payload, signature): return True
    def commit_pair_and_audit(self, authorization_id, nonce_records, audit_event): return True
    def healthcheck(self): return True


def valid_bundle():
    adapters = [Adapter() for _ in range(6)]
    return ProductionAdapterBundle(*adapters)


def test_complete_declared_bundle_passes_structural_preflight():
    validate_production_adapter_bundle(valid_bundle())


def test_missing_bundle_fails_closed():
    with pytest.raises(ProductionAdapterContractError):
        validate_production_adapter_bundle(None)


def test_adapter_without_production_declaration_fails_closed():
    bundle = valid_bundle()
    object.__setattr__(bundle.ledger, "production_grade", False)
    with pytest.raises(ProductionAdapterContractError, match="ledger"):
        validate_production_adapter_bundle(bundle)


def test_missing_atomic_ledger_healthcheck_fails_closed():
    bundle = valid_bundle()

    class IncompleteLedger:
        production_grade = True

        def commit_pair_and_audit(self, authorization_id, nonce_records, audit_event):
            return True

    object.__setattr__(bundle, "ledger", IncompleteLedger())
    with pytest.raises(ProductionAdapterContractError, match="healthcheck"):
        validate_production_adapter_bundle(bundle)


def test_bundle_requires_all_six_adapter_roles():
    with pytest.raises(TypeError):
        ProductionAdapterBundle(None, None, None, None, None)

def test_structural_preflight_never_calls_adapters_or_returns_authorization():
    class NoCallAdapter:
        production_grade = True

        def __getattribute__(self, name):
            if name in {
                "resolve_signing_key", "load_approval_session", "has_current_role",
                "sign", "verify", "commit_pair_and_audit", "healthcheck",
            }:
                raise AssertionError("Preflight must not invoke provider operations")
            return object.__getattribute__(self, name)

    bundle = ProductionAdapterBundle(*(NoCallAdapter() for _ in range(6)))

    result = validate_production_adapter_bundle(bundle)

    # Structural completeness is not provider verification, an approval, or
    # an execution capability. The function intentionally returns no token.
    assert result is None
    assert not hasattr(result, "execution_authorized")
    assert not hasattr(result, "g2b_status")

