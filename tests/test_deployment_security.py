"""Regression tests for public deployment authentication safeguards."""

import pytest

from deployment_security import (
    deployment_auth_required,
    validate_deployment_security,
)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", True])
def test_auth_required_accepts_explicit_true_values(value):
    assert deployment_auth_required(value) is True


@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off", False])
def test_auth_required_is_false_without_explicit_true_value_in_local_mode(value):
    assert deployment_auth_required(value) is False


@pytest.mark.parametrize("value", [None, "", "false", "0", "no", "off", False])
def test_public_url_forces_authentication_even_if_opt_out_is_set(value):
    assert deployment_auth_required(value, "https://sowia.streamlit.app") is True


def test_public_url_with_missing_supabase_fails_closed():
    auth_required = deployment_auth_required("false", "https://sowia.streamlit.app")
    with pytest.raises(RuntimeError, match="Supabase manquante"):
        validate_deployment_security(auth_required, False)


def test_required_authentication_fails_closed_without_supabase():
    with pytest.raises(RuntimeError, match="Supabase manquante"):
        validate_deployment_security(True, False)


def test_required_authentication_allows_configured_supabase():
    assert validate_deployment_security(True, True) is None


def test_local_development_mode_remains_available_without_supabase():
    assert validate_deployment_security(False, False) is None


def test_optional_authentication_allows_configured_supabase():
    assert validate_deployment_security(False, True) is None
