from types import SimpleNamespace
import pytest
from app.services import rate_limit

class FakeRpc:
    def __init__(self, error=None):
        self.error = error
    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data={"accepted": True})

class FakeClient:
    def __init__(self, error=None):
        self.error = error
        self.calls = []
    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRpc(self.error)

def test_rate_limit_uses_atomic_rpc(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(rate_limit, "get_service_client", lambda: client)
    rate_limit.check_generation_rate_limit(user_id="user-1", limit=3, window_seconds=60)
    assert client.calls[0][0] == "check_generation_rate_limit"
    assert client.calls[0][1]["p_limit"] == 3
    assert client.calls[0][1]["p_bucket"] == "image_generation"

def test_rate_limit_maps_atomic_rejection(monkeypatch):
    client = FakeClient(Exception("RATE_LIMIT_EXCEEDED"))
    monkeypatch.setattr(rate_limit, "get_service_client", lambda: client)
    with pytest.raises(rate_limit.RateLimitExceeded):
        rate_limit.check_generation_rate_limit(user_id="user-1")
