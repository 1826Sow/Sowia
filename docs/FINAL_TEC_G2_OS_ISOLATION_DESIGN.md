# FINAL TEC — G2 design for an isolated execution boundary

## Status and scope

Design specification only. This document does not implement or launch a sandbox,
container, VM, runner, host configuration, or workload.

This design is downstream of G0 authorization and G1's fixed synthetic-fixture
evaluator. G1's targeted CI has now passed on PR #243: compilation succeeded and
55 focused G0/G1 tests passed. G2-A static profile validation is being implemented
separately in draft PR #245. Neither result demonstrates a real OS-level boundary.

## Security objective

If a later approved stage executes a workload, it must execute in a disposable
boundary with explicit resource ceilings, no ambient credentials, no host control
sockets, and no network by default. The control plane must remain outside the workload
boundary.

A container is defense in depth, not a sufficient boundary for hostile multi-tenant
code by itself. For untrusted code or stronger tenant separation, prefer a disposable
microVM/VM boundary (for example, a Firecracker-class microVM) with a minimal guest
and a separately enforced host policy. The choice requires a threat-model review and
must not be assumed to be available on the current hosting platform.

## Threat model

Protect against:
- workload attempts to read host files, environment secrets, credentials, or other tenants' data;
- privilege escalation, capability abuse, namespace escape, and access to container/runtime sockets;
- fork bombs, memory exhaustion, CPU monopolization, disk exhaustion, and excessive process creation;
- network egress, DNS tunnelling, metadata-service access, lateral movement, and provider API calls;
- stale or replayed authorization, tampered manifests, and forged execution evidence;
- incomplete cleanup after timeout, crash, or emergency stop.

Out of scope for a first prototype:
- protection against a compromised host kernel, hypervisor, cloud control plane, or malicious infrastructure operator;
- proof that a container is equivalent to a hardware security boundary;
- production multi-tenant execution before independent security review.

## Required architecture

1. **Control plane outside the sandbox**: authenticate the operator, validate the G0 manifest, check expiry and approval, enforce a unique run ID and one-time authorization nonce, and record the policy decision.
2. **Immutable execution package**: pinned image by digest, explicit entrypoint and arguments, read-only workload input, declared output schema, and recorded software bill of materials. No arbitrary image tags or runtime package installation.
3. **Disposable isolation boundary**: rootless runtime where feasible; user and PID/mount/network namespaces; non-root UID/GID; no privileged mode; all Linux capabilities dropped; `no_new_privileges`; seccomp allowlist; AppArmor or SELinux profile where supported.
4. **Filesystem**: read-only root filesystem; only a size-limited temporary scratch mount; no host home, Docker/containerd socket, cloud credentials, SSH agent, host `/proc` view, or sensitive device mounts.
5. **Network**: no network namespace interfaces or egress by default; deny DNS and metadata-service access; enforce deny at the host/firewall layer too. Any future allowlist requires separate written approval and explicit destination/port scope.
6. **Resource enforcement**: cgroups v2 limits for CPU, memory, process count, and I/O; bounded scratch storage and output bytes; wall-clock timeout; request and repetition ceilings. Limits must be enforced by the runtime/host, not merely declared in a manifest.
7. **Emergency stop**: control-plane kill of the entire cgroup/container/VM, including descendants; revoke the run nonce; prevent automatic restart/retry; record stop reason and cleanup result.
8. **Evidence**: hash the immutable manifest, image digest, policy version, and output artifacts; record timestamps and exit status. Hashes alone do not prove identity, execution, or truth. Independent review remains mandatory before any evidence can become verified or published.

## Fail-closed launch sequence

`draft → submitted → authorized → prepared → running → completed → pending_review`

Before launch, reject if any authorization is missing/expired/replayed, image digest is unpinned, runtime isolation feature is unavailable, network policy cannot be enforced, resource controller is unavailable, output quota is missing, or emergency stop is active.

On any limit breach, timeout, runtime error, unexpected network interface, or cleanup failure: terminate the entire workload boundary, mark the run aborted/failed, preserve a minimal audit record, and do not retry automatically.

No transition from this design directly sets evidence to `verified` or publication to `published`.

## G2 verification gates

- **G2-A static policy tests**: a separate validator and test suite check the declared runtime profile for privileged mode, host namespaces, host mounts, runtime sockets, capabilities, unpinned images, network access, and resource ceilings. Draft PR #245 implements this descriptor-only check; it does not enforce or inspect host controls.
- **G2-B disposable local smoke tests**: benign fixed test process only; verify namespace and read-only filesystem behavior. No user-supplied code.
- **G2-C resource enforcement tests**: deliberately bounded CPU/memory/process/output/time test fixtures; confirm host-enforced termination and cleanup.
- **G2-D network denial tests**: prove DNS, metadata, loopback escape paths, and egress are blocked from inside the boundary and at the host layer.
- **G2-E stop/recovery tests**: stop during execution; confirm descendants terminate, no restart occurs, authorization is consumed, and audit record is retained.
- **G2-F independent review**: security review of host/runtime configuration and threat model before any untrusted workload.

Each gate requires captured logs, exact runtime/version/configuration, reproducible test commands, and reviewer sign-off. A passing unit test is not proof of a deployed security boundary.

## Explicit approvals required before implementation or execution

Separate approval is required for:
- selecting the host/runtime and any provider;
- installing or changing host software/configuration;
- enabling network access or allowlists;
- running any workload beyond bundled benign fixtures;
- provisioning compute, storage, or other paid resources;
- connecting Supabase, secrets, investor access, or publication paths.

## Current project boundary

This document does not select a provider or runtime, modify SOWIA application behavior,
touch Supabase, create secrets, run commands on a host, provision resources, contact
vendors, publish metrics, or spend money. FINAL TEC remains a proposed future product
within the SOWIA project, not an operational independent platform.
