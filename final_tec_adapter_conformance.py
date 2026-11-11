"""Fail-closed execution harness for provider-specific adapter conformance probes.

The harness records only check names and outcomes. Probe implementations must
avoid returning or embedding credentials, tokens, signatures, or personal data.
A passing fake-probe suite is not evidence that a real provider was tested.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


@dataclass(frozen=True)
class ConformanceProbe:
    name: str
    execute: Callable[[], bool]


@dataclass(frozen=True)
class ConformanceResult:
    name: str
    passed: bool
    failure_code: str | None = None


@dataclass(frozen=True)
class ConformanceReport:
    status: str
    results: tuple[ConformanceResult, ...]

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


class ConformanceConfigurationError(ValueError):
    """Raised when the conformance suite is empty or ambiguous."""


def run_adapter_conformance(
    probes: Sequence[ConformanceProbe],
) -> ConformanceReport:
    """Run explicit probes; any false result or exception makes the suite fail.

    Exception messages are deliberately not copied into the report because
    provider SDK exceptions can contain sensitive request or response data.
    """
    if not isinstance(probes, Sequence) or isinstance(probes, (str, bytes)):
        raise ConformanceConfigurationError(
            "The conformance suite must be a finite sequence"
        )
    if not probes:
        raise ConformanceConfigurationError("At least one conformance probe is required")
    if any(not isinstance(probe, ConformanceProbe) for probe in probes):
        raise ConformanceConfigurationError(
            "Every suite entry must be a ConformanceProbe"
        )

    names = [probe.name for probe in probes]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ConformanceConfigurationError("Probe names must be non-empty strings")
    if len(set(names)) != len(names):
        raise ConformanceConfigurationError("Probe names must be unique")
    if any(not callable(probe.execute) for probe in probes):
        raise ConformanceConfigurationError("Every probe must have a callable executor")

    results: list[ConformanceResult] = []
    for probe in probes:
        try:
            outcome = probe.execute()
            if outcome is True:
                results.append(ConformanceResult(probe.name, True))
            else:
                results.append(ConformanceResult(probe.name, False, "PROBE_REJECTED"))
        except Exception:
            results.append(ConformanceResult(probe.name, False, "PROBE_EXCEPTION"))

    status = "PASS" if all(result.passed for result in results) else "FAIL"
    return ConformanceReport(status=status, results=tuple(results))
