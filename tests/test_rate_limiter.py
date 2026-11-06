"""Tests for fail-closed shared Supabase rate limiting."""
from types import SimpleNamespace

import pytest

import rate_limiter


class User:
    id = "user-123"


class FakeRpc:
    def __init__(self, data=None, error=None):
        self.data, self.error = data, error
        self.name = None
        self.params = None

    def rpc(self, name, params):
        self.name, self.params = name, params
        return self

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.data)


def test_consumes_quota_through_authenticated_rpc():
    client = FakeRpc([{"allowed": True, "remaining": 4, "reset_at": "2030-01-01T00:01:00Z"}])
    result = rate_limiter.consume_rate_limit(client, User(), "assistant")
    assert result.allowed is True
    assert result.remaining == 4
    assert client.name == "sowia_consume_rate_limit"
    assert client.params == {"p_bucket_key": "assistant"}


def test_denies_when_quota_is_exhausted():
    client = FakeRpc([{"allowed": False, "remaining": 0, "reset_at": "2030-01-01T00:01:00Z"}])
    with pytest.raises(rate_limiter.RateLimitExceeded):
        rate_limiter.consume_rate_limit(client, User(), "assistant")


def test_fails_closed_when_rpc_is_unavailable():
    client = FakeRpc(error=TimeoutError("private provider detail"))
    with pytest.raises(rate_limiter.RateLimitUnavailable):
        rate_limiter.consume_rate_limit(client, User(), "assistant")


@pytest.mark.parametrize("data", [None, [], [{}], [{"allowed": 1, "remaining": 0, "reset_at": "x"}],
                                  [{"allowed": True, "remaining": True, "reset_at": "x"}]])
def test_fails_closed_on_malformed_rpc_response(data):
    with pytest.raises(rate_limiter.RateLimitUnavailable):
        rate_limiter.consume_rate_limit(FakeRpc(data), User(), "assistant")


def test_rejects_anonymous_user_before_rpc():
    class Client:
        def rpc(self, *args, **kwargs):
            raise AssertionError("RPC must not be called")
    with pytest.raises(PermissionError):
        rate_limiter.consume_rate_limit(Client(), None, "assistant")


def test_rejects_unknown_bucket_before_rpc():
    class Client:
        def rpc(self, *args, **kwargs):
            raise AssertionError("RPC must not be called")
    with pytest.raises(ValueError):
        rate_limiter.consume_rate_limit(Client(), User(), "unlimited")
