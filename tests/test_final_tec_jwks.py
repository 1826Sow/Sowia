import json
from email.message import Message
from urllib.error import HTTPError

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from final_tec_jwks import HTTPSJWKSResolver, JWKSConfigurationError


ISSUER = "https://login.example.test/"
JWKS = "https://login.example.test/.well-known/jwks.json"


def jwk(kid):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    value = json.loads(__import__("jwt").algorithms.RSAAlgorithm.to_jwk(key))
    value.update({"kid": kid, "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    return value


class Response:
    def __init__(self, document, *, content_type="application/json", cache_control="max-age=60", status=200):
        self.body = json.dumps(document).encode()
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["Cache-Control"] = cache_control
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def read(self, size=-1):
        return self.body[:size]


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_resolver(opener, **kwargs):
    return HTTPSJWKSResolver(
        issuer=ISSUER,
        jwks_url=JWKS,
        allowed_origins=["https://login.example.test"],
        opener=opener,
        **kwargs,
    )


def test_rejects_non_https_and_ambiguous_urls():
    for url in (
        "http://login.example.test/jwks",
        "https:///missing-host",
        "https://user:secret@login.example.test/jwks",
        "https://login.example.test/jwks?tenant=x",
        "https://login.example.test/jwks#fragment",
    ):
        with pytest.raises(JWKSConfigurationError):
            HTTPSJWKSResolver(
                issuer=ISSUER,
                jwks_url=url,
                allowed_origins=["https://login.example.test"],
            )


def test_rejects_jwks_origin_not_explicitly_allowlisted():
    with pytest.raises(JWKSConfigurationError):
        HTTPSJWKSResolver(
            issuer=ISSUER,
            jwks_url="https://attacker.example/jwks",
            allowed_origins=["https://login.example.test"],
        )

def test_rejects_issuer_origin_missing_from_allowlist():
    with pytest.raises(JWKSConfigurationError):
        HTTPSJWKSResolver(
            issuer=ISSUER,
            jwks_url=JWKS,
            allowed_origins=["https://other.example"],
        )


def test_rejects_issuer_origin_even_when_jwks_origin_is_allowlisted():
    with pytest.raises(JWKSConfigurationError):
        HTTPSJWKSResolver(
            issuer="https://untrusted-issuer.example/",
            jwks_url=JWKS,
            allowed_origins=["https://login.example.test"],
        )


def test_resolves_rsa_rs256_key_and_uses_bounded_cache():
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, cache_control="max-age=99999")])
    resolver = make_resolver(opener, cache_ttl_seconds=60, max_cache_ttl_seconds=120)
    assert resolver("key-1") is not None
    assert resolver("key-1") is not None
    assert len(opener.calls) == 1
    assert opener.calls[0][1] == 3.0


def test_unknown_kid_triggers_one_refresh_for_rotation_then_fails_closed():
    opener = FakeOpener([
        Response({"keys": [jwk("old-key")]}),
        Response({"keys": [jwk("new-key")]}),
        Response({"keys": [jwk("new-key")]}),
    ])
    resolver = make_resolver(opener)
    assert resolver("old-key") is not None
    assert resolver("new-key") is not None
    assert len(opener.calls) == 2
    assert resolver("not-present") is None
    assert len(opener.calls) == 3


@pytest.mark.parametrize("content_type", [
    "application/json; charset=utf-8",
    "application/jwk-set+json",
])
def test_accepts_standard_jwks_json_media_types(content_type):
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, content_type=content_type)])
    assert make_resolver(opener)("key-1") is not None


@pytest.mark.parametrize("content_type", [
    "text/json",
    "application/notjson",
    "application/jsonp",
    "application/not a token+json",
    "application/xml",
])
def test_rejects_non_jwks_json_media_types(content_type):
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, content_type=content_type)])
    with pytest.raises(JWKSConfigurationError, match="accepted JSON media type"):
        make_resolver(opener)("key-1")


class ReadFailureResponse(Response):
    def read(self, size=-1):
        raise OSError("sensitive body read detail")


def test_incomplete_http_response_is_normalized():
    from http.client import IncompleteRead

    opener = FakeOpener([IncompleteRead(b"partial", 20)])
    with pytest.raises(JWKSConfigurationError, match="could not be reached safely"):
        make_resolver(opener)("key-1")


def test_body_read_network_failure_is_normalized():
    opener = FakeOpener([ReadFailureResponse({"keys": [jwk("key-1")]})])
    with pytest.raises(JWKSConfigurationError, match="could not be reached safely") as error:
        make_resolver(opener)("key-1")
    assert "sensitive" not in str(error.value)


def test_rejects_non_json_response():
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, content_type="text/html")])
    with pytest.raises(JWKSConfigurationError):
        make_resolver(opener)("key-1")


def test_rejects_duplicate_kids():
    duplicate = jwk("duplicate")
    opener = FakeOpener([Response({"keys": [duplicate, duplicate]})])
    with pytest.raises(JWKSConfigurationError):
        make_resolver(opener)("duplicate")

def test_rejects_private_rsa_material_in_jwks():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_jwk = json.loads(__import__("jwt").algorithms.RSAAlgorithm.to_jwk(private_key))
    private_jwk.update({"kid": "private-key", "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    opener = FakeOpener([Response({"keys": [private_jwk]})])
    with pytest.raises(JWKSConfigurationError, match="private RSA parameters"):
        make_resolver(opener)("private-key")


def test_rejects_rsa_keys_below_2048_bits():
    weak_key = rsa.generate_private_key(public_exponent=65537, key_size=1024).public_key()
    weak_jwk = json.loads(__import__("jwt").algorithms.RSAAlgorithm.to_jwk(weak_key))
    weak_jwk.update({"kid": "weak-key", "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    opener = FakeOpener([Response({"keys": [weak_jwk]})])
    with pytest.raises(JWKSConfigurationError, match="at least 2048 bits"):
        make_resolver(opener)("weak-key")


def test_rejects_weak_rsa_public_exponent():
    weak_exponent_key = rsa.generate_private_key(public_exponent=3, key_size=2048).public_key()
    weak_jwk = json.loads(__import__("jwt").algorithms.RSAAlgorithm.to_jwk(weak_exponent_key))
    weak_jwk.update({"kid": "weak-exponent", "alg": "RS256", "use": "sig", "key_ops": ["verify"]})
    opener = FakeOpener([Response({"keys": [weak_jwk]})])
    with pytest.raises(JWKSConfigurationError, match="public exponent is too weak"):
        make_resolver(opener)("weak-exponent")


def test_http_redirect_is_fail_closed():
    redirect = HTTPError(JWKS, 302, "Found", Message(), None)
    opener = FakeOpener([redirect])
    with pytest.raises(JWKSConfigurationError):
        make_resolver(opener)("key-1")


def test_rejects_oversized_response():
    opener = FakeOpener([Response({"keys": [jwk("key-1")]})])
    resolver = make_resolver(opener, max_response_bytes=1024)
    response = opener.responses[0]
    response.body = b" " * 1025
    with pytest.raises(JWKSConfigurationError):
        resolver("key-1")


@pytest.mark.parametrize("kwargs", [
    {"cache_ttl_seconds": True},
    {"max_cache_ttl_seconds": True},
    {"timeout_seconds": True},
    {"max_response_bytes": True},
])
def test_rejects_boolean_numeric_configuration(kwargs):
    with pytest.raises(JWKSConfigurationError):
        make_resolver(FakeOpener([]), **kwargs)


@pytest.mark.parametrize("cache_control", ["max-age=0", "no-store", "no-cache", "public, max-age=0"])
def test_non_reusable_cache_control_forces_fetch_on_each_call(cache_control):
    opener = FakeOpener([
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
    ])
    resolver = make_resolver(opener)
    assert resolver("key-1") is not None
    assert resolver("key-1") is not None
    assert len(opener.calls) == 2


def test_quoted_max_age_is_respected():
    opener = FakeOpener([
        Response({"keys": [jwk("key-1")]}, cache_control='public, max-age="60"')
    ])
    resolver = make_resolver(opener)
    assert resolver("key-1") is not None
    assert resolver("key-1") is not None
    assert len(opener.calls) == 1


@pytest.mark.parametrize("cache_control", [
    "max-age=60, max-age=0",
    'max-age="60',
    'max-age=60"',
    "max-age=sixty",
])
def test_ambiguous_or_malformed_max_age_forces_fetch_on_each_call(cache_control):
    opener = FakeOpener([
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
    ])
    resolver = make_resolver(opener)
    assert resolver("key-1") is not None
    assert resolver("key-1") is not None
    assert len(opener.calls) == 2


@pytest.mark.parametrize("cache_control", [
    "max-age=" + "9" * 5000,
    "max-age=１２",
])
def test_extreme_or_non_ascii_max_age_forces_fetch_on_each_call(cache_control):
    opener = FakeOpener([
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
        Response({"keys": [jwk("key-1")]}, cache_control=cache_control),
    ])
    resolver = make_resolver(opener)
    assert resolver("key-1") is not None
    assert resolver("key-1") is not None
    assert len(opener.calls) == 2


@pytest.mark.parametrize("network_error", [
    TimeoutError("sensitive timeout detail"),
    OSError("sensitive socket detail"),
])
def test_network_failures_are_normalized_without_stale_key_fallback(network_error):
    now = [100.0]
    opener = FakeOpener([
        Response({"keys": [jwk("key-1")]}),
        network_error,
    ])
    resolver = make_resolver(opener, cache_ttl_seconds=1, max_cache_ttl_seconds=2,
                             clock=lambda: now[0])
    assert resolver("key-1") is not None
    now[0] = 102.0
    with pytest.raises(JWKSConfigurationError, match="could not be reached safely") as error:
        resolver("key-1")
    assert "sensitive" not in str(error.value)
    assert len(opener.calls) == 2


def test_url_error_is_normalized():
    from urllib.error import URLError

    opener = FakeOpener([URLError("sensitive provider detail")])
    with pytest.raises(JWKSConfigurationError, match="could not be reached safely") as error:
        make_resolver(opener)("key-1")
    assert "sensitive" not in str(error.value)
