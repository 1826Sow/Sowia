from types import SimpleNamespace

from final_tec_access import authorize_final_tec_investor_viewer


class FakeRpc:
    def __init__(self, data=True, error=None):
        self.data = data
        self.error = error
        self.called = False

    def execute(self):
        self.called = True
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.data)


class FakeSupabase:
    def __init__(self, rpc_result=None):
        self.rpc_result = rpc_result
        self.function_name = None

    def rpc(self, function_name):
        self.function_name = function_name
        return self.rpc_result


def test_active_investor_assignment_is_confirmed_by_server_rpc():
    rpc = FakeRpc(data=True)
    client = FakeSupabase(rpc)

    assert authorize_final_tec_investor_viewer(client, SimpleNamespace(id="user-1")) is True
    assert client.function_name == "final_tec_can_view_published_metrics"
    assert rpc.called


def test_false_rpc_result_denies_access():
    client = FakeSupabase(FakeRpc(data=False))

    assert authorize_final_tec_investor_viewer(client, SimpleNamespace(id="user-1")) is False


def test_missing_identity_or_client_denies_access():
    assert authorize_final_tec_investor_viewer(None, SimpleNamespace(id="user-1")) is False
    assert authorize_final_tec_investor_viewer(FakeSupabase(FakeRpc()), None) is False
    assert authorize_final_tec_investor_viewer(FakeSupabase(FakeRpc()), SimpleNamespace(id="")) is False


def test_missing_rpc_denies_access():
    assert authorize_final_tec_investor_viewer(object(), SimpleNamespace(id="user-1")) is False


def test_rpc_failure_denies_access():
    client = FakeSupabase(FakeRpc(error=RuntimeError("database unavailable")))

    assert authorize_final_tec_investor_viewer(client, SimpleNamespace(id="user-1")) is False


def test_malformed_rpc_result_denies_access():
    client = FakeSupabase(FakeRpc(data=[True]))

    assert authorize_final_tec_investor_viewer(client, SimpleNamespace(id="user-1")) is False
