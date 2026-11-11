import pytest

from final_tec_adapter_conformance import (
    ConformanceConfigurationError,
    ConformanceProbe,
    run_adapter_conformance,
)


def test_all_positive_probes_pass():
    report = run_adapter_conformance([
        ConformanceProbe("oidc-invalid-issuer-rejected", lambda: True),
        ConformanceProbe("ledger-duplicate-nonce-rejected", lambda: True),
    ])
    assert report.passed is True
    assert report.status == "PASS"
    assert all(result.passed for result in report.results)


def test_one_negative_probe_fails_entire_suite():
    report = run_adapter_conformance([
        ConformanceProbe("valid-token-accepted", lambda: True),
        ConformanceProbe("revoked-key-rejected", lambda: False),
    ])
    assert report.passed is False
    assert report.status == "FAIL"
    assert report.results[1].failure_code == "PROBE_REJECTED"


def test_probe_exception_fails_without_leaking_exception_message():
    def broken_provider_call():
        raise RuntimeError("sensitive token=do-not-copy")

    report = run_adapter_conformance([
        ConformanceProbe("provider-unavailable-fails-closed", broken_provider_call),
    ])
    assert report.passed is False
    assert report.results[0].failure_code == "PROBE_EXCEPTION"
    assert "sensitive" not in repr(report)


@pytest.mark.parametrize("probes", [[], ()])
def test_empty_suite_is_rejected(probes):
    with pytest.raises(ConformanceConfigurationError):
        run_adapter_conformance(probes)


def test_duplicate_probe_names_are_rejected():
    with pytest.raises(ConformanceConfigurationError, match="unique"):
        run_adapter_conformance([
            ConformanceProbe("same", lambda: True),
            ConformanceProbe("same", lambda: True),
        ])


def test_non_boolean_truthy_probe_result_does_not_pass():
    report = run_adapter_conformance([
        ConformanceProbe("strict-bool", lambda: 1),
    ])
    assert report.passed is False



@pytest.mark.parametrize(
    ("probes", "message"),
    [
        ([None], "ConformanceProbe"),
        (["not-a-probe"], "ConformanceProbe"),
        ("not-a-suite", "finite sequence"),
    ],
)
def test_malformed_suite_entries_are_rejected(probes, message):
    with pytest.raises(ConformanceConfigurationError, match=message):
        run_adapter_conformance(probes)


@pytest.mark.parametrize("name", [None, 1, "", "   "])
def test_invalid_probe_names_are_rejected(name):
    with pytest.raises(ConformanceConfigurationError, match="non-empty strings"):
        run_adapter_conformance([ConformanceProbe(name, lambda: True)])



def test_one_shot_generator_is_rejected_instead_of_passing_empty_suite():
    probes = (probe for probe in [
        ConformanceProbe("must-run", lambda: True),
    ])
    with pytest.raises(ConformanceConfigurationError, match="finite sequence"):
        run_adapter_conformance(probes)
