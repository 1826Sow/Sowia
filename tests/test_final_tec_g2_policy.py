from copy import deepcopy

import pytest

from final_tec_g2_policy import (
    IsolationPolicyError,
    validate_static_isolation_profile,
)


def valid_profile():
    return {
        "runtime": {
            "runtime_class": "rootless_container",
            "runtime_version": "declared-runtime-version",
            "image_digest": "sha256:" + "a" * 64,
            "privileged": False,
            "uid": 10001,
            "gid": 10001,
            "restart_policy": "never",
        },
        "namespaces": {"user": True, "pid": True, "mount": True, "network": True},
        "filesystem": {
            "root_read_only": True,
            "scratch_mb": 128,
            "host_mounts": [],
            "runtime_socket_mounts": [],
            "credential_mounts": [],
            "device_mounts": [],
            "host_proc": False,
        },
        "security": {
            "no_new_privileges": True,
            "capabilities_drop": ["ALL"],
            "seccomp_profile": "seccomp-allowlist-v1",
            "apparmor_profile": "final-tec-restricted",
            "selinux_profile": None,
        },
        "network": {
            "enabled": False,
            "egress": False,
            "dns": False,
            "metadata_access": False,
        },
        "resources": {
            "cgroup_v2": True,
            "cpu_cores": 1,
            "memory_mb": 256,
            "pids_limit": 32,
            "io_limit_mb": 128,
            "output_bytes_limit": 262144,
            "timeout_seconds": 15,
        },
    }


def test_valid_profile_is_only_static_and_never_executable():
    result = validate_static_isolation_profile(valid_profile())
    assert result["policy_result"] == "static_profile_validated_not_enforced"
    assert result["execution_permitted"] is False
    assert result["runtime_started"] is False
    assert result["host_controls_verified"] is False
    assert result["evidence_status"] == "pending"
    assert result["publication_state"] == "draft"
    assert result["limits"]["timeout_seconds"] == 15


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("runtime", "runtime_class"), "privileged_container"),
        (("runtime", "privileged"), True),
        (("runtime", "image_digest"), "latest"),
        (("runtime", "uid"), 0),
        (("runtime", "gid"), 0),
        (("runtime", "restart_policy"), "always"),
        (("namespaces", "user"), False),
        (("namespaces", "pid"), False),
        (("namespaces", "mount"), False),
        (("namespaces", "network"), False),
        (("filesystem", "root_read_only"), False),
        (("filesystem", "host_proc"), True),
        (("filesystem", "host_mounts"), ["/:/host"]),
        (("filesystem", "runtime_socket_mounts"), ["/run/containerd.sock"]),
        (("filesystem", "credential_mounts"), ["/run/secrets"]),
        (("filesystem", "device_mounts"), ["/dev/kvm"]),
        (("security", "no_new_privileges"), False),
        (("security", "capabilities_drop"), ["NET_ADMIN"]),
        (("security", "seccomp_profile"), ""),
        (("security", "apparmor_profile"), None),
        (("network", "enabled"), True),
        (("network", "egress"), True),
        (("network", "dns"), True),
        (("network", "metadata_access"), True),
        (("resources", "cgroup_v2"), False),
        (("resources", "cpu_cores"), 3),
        (("resources", "memory_mb"), 513),
        (("resources", "pids_limit"), 65),
        (("resources", "io_limit_mb"), 513),
        (("resources", "output_bytes_limit"), 1_048_577),
        (("resources", "timeout_seconds"), 31),
    ],
)
def test_unsafe_or_unbounded_profile_is_rejected(path, value):
    profile = deepcopy(valid_profile())
    profile[path[0]][path[1]] = value
    with pytest.raises(IsolationPolicyError):
        validate_static_isolation_profile(profile)


def test_selinux_profile_can_replace_apparmor_profile():
    profile = valid_profile()
    profile["security"]["apparmor_profile"] = None
    profile["security"]["selinux_profile"] = "final-tec-selinux"
    assert validate_static_isolation_profile(profile)["execution_permitted"] is False


def test_missing_or_unknown_fields_fail_closed():
    profile = valid_profile()
    del profile["network"]["metadata_access"]
    with pytest.raises(IsolationPolicyError, match="absents"):
        validate_static_isolation_profile(profile)

    profile = valid_profile()
    profile["runtime"]["unexpected"] = "value"
    with pytest.raises(IsolationPolicyError, match="non autorisés"):
        validate_static_isolation_profile(profile)


@pytest.mark.parametrize("field", ["cpu_cores", "memory_mb", "pids_limit", "io_limit_mb", "output_bytes_limit", "timeout_seconds"])
def test_boolean_is_not_accepted_as_numeric_resource_limit(field):
    profile = valid_profile()
    profile["resources"][field] = True
    with pytest.raises(IsolationPolicyError):
        validate_static_isolation_profile(profile)


def test_missing_both_apparmor_and_selinux_profiles_fails_closed():
    profile = valid_profile()
    profile["security"]["apparmor_profile"] = None
    profile["security"]["selinux_profile"] = None
    with pytest.raises(IsolationPolicyError, match="AppArmor ou SELinux"):
        validate_static_isolation_profile(profile)


def test_invalid_top_level_shape_fails_closed():
    with pytest.raises(IsolationPolicyError):
        validate_static_isolation_profile([])
