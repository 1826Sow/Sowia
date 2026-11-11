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


def test_resolves_rsa_rs256_key_and_uses_bounded_cache():
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, cache_control="max-age=99999")])
    resolver = make_resolver(opener, max_cache_ttl_seconds=120)
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


def test_rejects_non_json_response():
    opener = FakeOpener([Response({"keys": [jwk("key-1")]}, content_type="text/html")])
    with pytest.raises(JWKSConfigurationError):
        make_resolver(opener)("key-1")


def test_rejects_duplicate_kids():
    duplicate = jwk("duplicate")
    opener = FakeOpener([Response({"keys": [duplicate, duplicate]})])
    with pytest.raises(JWKSConfigurationError):
        make_resolver(opener)("duplicate")


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
