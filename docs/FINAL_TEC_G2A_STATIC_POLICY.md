# FINAL TEC — G2-A static isolation policy validator

## Scope

G2-A adds a pure-Python validator for a declared isolation profile. It checks that
the profile describes a rootless, non-privileged container configuration with
pinned image digest, isolated namespaces, read-only root filesystem, no host mounts
or runtime/credential/device sockets, dropped capabilities, explicit seccomp and
AppArmor/SELinux profile, disabled network paths, and bounded resource limits.

## Strict limitation

This is **not enforcement** and does not inspect the host or runtime. It does not
launch a container or VM, configure namespaces, cgroups, firewall rules, AppArmor,
SELinux, or seccomp, and it does not prove that any declared control is active.
The output explicitly sets `execution_permitted=false`,
`runtime_started=false`, and `host_controls_verified=false`.

No provider or runtime product is selected. No user-supplied code is run. No network,
subprocess, filesystem operation, database, Supabase, secret, payment, or paid
resource is used by the validator.

## G2-A exit boundary

- Unit tests cover missing and unknown fields, privileged mode, host namespaces and
  mounts, runtime/credential/device sockets, capabilities, unpinned images, network
  paths, and resource ceilings.
- Passing these tests validates only the Python policy function and its test fixtures.
- Any later G2-B/C/D/E test requires a separate reviewed design and explicit approval
  before launching even a benign process or changing host/runtime configuration.
- Independent security review remains mandatory before any untrusted workload.

## Evidence state

All results remain `pending/draft`. A passing static policy test is not a security
certification, a deployed isolation boundary, or investor-facing performance evidence.
