# FINAL TEC — G1 offline synthetic fixture evaluator

## Purpose

G1 is deliberately narrower than a process/container sandbox. This first increment
evaluates two fixed, bundled synthetic datasets after the G0 fail-closed policy gate.
It does not execute arbitrary code or a benchmark workload.

## What the prototype does

- Accepts only the fixture identifiers returned by `available_fixtures()`.
- Validates the authorization manifest with `final_tec_runner_policy`.
- Requires the local sandbox resource, `local_fixture` cost basis, zero estimated
  cost, disabled network, and strict duration/request/repetition/CPU/memory/artifact
  ceilings.
- Computes descriptive statistics from immutable in-code samples.
- Returns explicit `synthetic_fixture_evaluation`, `workload_executed=false`,
  `network_used=false`, `provider_contacted=false`, and zero cost fields.
- Keeps all output at `pending/draft`; there is no verification or publication path.

## Explicit non-capabilities

This is not an OS-level sandbox, container, VM, process-isolation boundary, network
namespace, hardware benchmark, provider test, or proof that the host has no network.
No user-supplied code, command, path, plugin, URL, or dynamic fixture is executed or
loaded. No subprocess, socket, database, provider API, filesystem artifact, or payment
is used by the evaluator.

The latency values are fixed demonstration numbers, not observed timings. They must
never be presented as SOWIA/FINAL TEC performance, SLA, capacity, cost, or investor
evidence.

## G1 exit criteria before any broader sandbox

1. Unit tests for fixture allowlisting, manifest validation, and every resource cap.
2. Static review confirms no arbitrary execution, network, provider, DB, or payment path.
3. Independent review of the evaluator and its dependency on G0.
4. A separate design and approval for a genuine OS-level isolation layer (e.g. a
   locked-down ephemeral container or VM) before any user code or real workload is run.
5. Real workload/provider tests remain a later gate requiring explicit written
   authorization, a selected provider, and a hard approved budget.

## Targeted CI

The G0 base branch now contains a dedicated GitHub Actions workflow for pull requests
targeting that branch. It compiles the G0/G1 policy modules and runs only the focused
G0 and G1 unit-test files. The workflow is read-only and does not use secrets, network
services, Supabase, providers, or paid resources. Its result must be observed on the
updated PR before G1 can be considered CI-validated.

## Current status

Prototype code and unit tests only. The PR is based on the G0 branch and remains
unmerged/un-deployed. No workload was run, no external system was contacted, no
resource was provisioned, no secret or Supabase setting was changed, and no money
was spent.
