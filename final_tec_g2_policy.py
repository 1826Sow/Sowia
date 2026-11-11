"""G2-A static descriptor validator for FINAL TEC isolation policy.

This module validates declared sandbox settings only. It does not inspect the host,
launch a container or VM, enforce namespaces/cgroups/firewall rules, or prove that
the declared settings are active. All results remain pending/draft.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


class IsolationPolicyError(ValueError):
    """Raised when an isolation profile is incomplete or unsafe."""


_IMAGE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _object(value: Any, field: str, required: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IsolationPolicyError(f"{field} doit être un objet.")
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        raise IsolationPolicyError(
            f"Champs obligatoires absents dans {field}: " + ", ".join(missing)
        )
    if unknown:
        raise IsolationPolicyError(
            f"Champs non autorisés dans {field}: " + ", ".join(unknown)
        )
    return value


def _bounded_number(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise IsolationPolicyError(f"{field} doit être un entier.")
    if not minimum <= value <= maximum:
        raise IsolationPolicyError(
            f"{field} doit être compris entre {minimum} et {maximum}."
        )
    return value


def _empty_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or value:
        raise IsolationPolicyError(f"{field} doit être une liste vide.")


def validate_static_isolation_profile(
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a declared container-isolation profile without executing it."""
    top = _object(
        profile,
        "profile",
        {"runtime", "namespaces", "filesystem", "security", "network", "resources"},
    )
    runtime = _object(
        top["runtime"],
        "runtime",
        {"runtime_class", "runtime_version", "image_digest", "privileged", "uid", "gid", "restart_policy"},
    )
    namespaces = _object(
        top["namespaces"],
        "namespaces",
        {"user", "pid", "mount", "network"},
    )
    filesystem = _object(
        top["filesystem"],
        "filesystem",
        {"root_read_only", "scratch_mb", "host_mounts", "runtime_socket_mounts", "credential_mounts", "device_mounts", "host_proc"},
    )
    security = _object(
        top["security"],
        "security",
        {"no_new_privileges", "capabilities_drop", "seccomp_profile", "apparmor_profile", "selinux_profile"},
    )
    network = _object(
        top["network"],
        "network",
        {"enabled", "egress", "dns", "metadata_access"},
    )
    resources = _object(
        top["resources"],
        "resources",
        {"cgroup_v2", "cpu_cores", "memory_mb", "pids_limit", "io_limit_mb", "output_bytes_limit", "timeout_seconds"},
    )

    if runtime["runtime_class"] != "rootless_container":
        raise IsolationPolicyError("G2-A exige le profil déclaré rootless_container.")
    if not isinstance(runtime["runtime_version"], str) or not runtime["runtime_version"].strip():
        raise IsolationPolicyError("La version du runtime est obligatoire.")
    digest = runtime["image_digest"]
    if not isinstance(digest, str) or not _IMAGE_DIGEST.fullmatch(digest):
        raise IsolationPolicyError("L'image doit être épinglée par digest SHA-256.")
    if runtime["privileged"] is not False:
        raise IsolationPolicyError("Le mode privileged est interdit.")
    for field in ("uid", "gid"):
        _bounded_number(runtime[field], f"runtime.{field}", minimum=1, maximum=65535)
    if runtime["restart_policy"] != "never":
        raise IsolationPolicyError("Le redémarrage automatique doit être désactivé.")

    for field in ("user", "pid", "mount", "network"):
        if namespaces[field] is not True:
            raise IsolationPolicyError(f"Namespace isolé obligatoire: {field}.")

    if filesystem["root_read_only"] is not True:
        raise IsolationPolicyError("Le système de fichiers racine doit être en lecture seule.")
    _bounded_number(filesystem["scratch_mb"], "filesystem.scratch_mb", minimum=1, maximum=1024)
    for field in ("host_mounts", "runtime_socket_mounts", "credential_mounts", "device_mounts"):
        _empty_list(filesystem[field], f"filesystem.{field}")
    if filesystem["host_proc"] is not False:
        raise IsolationPolicyError("L'accès à la vue /proc de l'hôte est interdit.")

    if security["no_new_privileges"] is not True:
        raise IsolationPolicyError("no_new_privileges doit être actif.")
    caps = security["capabilities_drop"]
    if not isinstance(caps, list) or caps != ["ALL"]:
        raise IsolationPolicyError("Toutes les capacités Linux doivent être supprimées (ALL).")
    if not isinstance(security["seccomp_profile"], str) or not security["seccomp_profile"].strip():
        raise IsolationPolicyError("Un profil seccomp explicite est obligatoire.")
    apparmor = security["apparmor_profile"]
    selinux = security["selinux_profile"]
    apparmor_ok = isinstance(apparmor, str) and bool(apparmor.strip())
    selinux_ok = isinstance(selinux, str) and bool(selinux.strip())
    if not (apparmor_ok or selinux_ok):
        raise IsolationPolicyError("Un profil AppArmor ou SELinux explicite est obligatoire.")

    for field in ("enabled", "egress", "dns", "metadata_access"):
        if network[field] is not False:
            raise IsolationPolicyError(f"Le contrôle réseau {field} doit être désactivé.")

    if resources["cgroup_v2"] is not True:
        raise IsolationPolicyError("La présence déclarée de cgroups v2 est obligatoire.")
    limits = {
        "cpu_cores": (1, 2),
        "memory_mb": (64, 512),
        "pids_limit": (1, 64),
        "io_limit_mb": (1, 512),
        "output_bytes_limit": (1, 1_048_576),
        "timeout_seconds": (1, 30),
    }
    normalized_limits = {
        field: _bounded_number(resources[field], f"resources.{field}", minimum=low, maximum=high)
        for field, (low, high) in limits.items()
    }

    checks = [
        "pinned_image_digest",
        "non_privileged_rootless_profile_declared",
        "isolated_namespaces_declared",
        "read_only_root_and_empty_host_mounts",
        "capabilities_dropped_and_security_profile_declared",
        "network_and_egress_disabled",
        "bounded_resource_profile_declared",
        "automatic_restart_disabled",
    ]
    return {
        "policy_result": "static_profile_validated_not_enforced",
        "checks_passed": checks,
        "limits": normalized_limits,
        "execution_permitted": False,
        "runtime_started": False,
        "host_controls_verified": False,
        "evidence_status": "pending",
        "publication_state": "draft",
        "notice": (
            "Validation statique des paramètres déclarés uniquement. "
            "Aucun contrôle hôte, runtime, cgroup, namespace ou pare-feu n'a été exécuté."
        ),
    }
