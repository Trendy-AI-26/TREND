import pytest

from app import db
from app.services import rate_limit


class FakeDb:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def fetch_one(self, sql, params=None, **_kwargs):
        self.calls.append((sql, params))
        if self.error:
            raise self.error
        return {"result": {"accepted": True}}


def test_rate_limit_uses_atomic_function(monkeypatch):
    fake = FakeDb()
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    rate_limit.check_generation_rate_limit(user_id="user-1", limit=3, window_seconds=60)
    sql, params = fake.calls[0]
    assert "check_generation_rate_limit" in sql
    assert params["p_limit"] == 3
    assert params["p_bucket"] == "image_generation"
    assert params["p_user_id"] == "user-1"


def test_rate_limit_maps_atomic_rejection(monkeypatch):
    fake = FakeDb(Exception("RATE_LIMIT_EXCEEDED"))
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    with pytest.raises(rate_limit.RateLimitExceeded):
        rate_limit.check_generation_rate_limit(user_id="user-1")


def test_rate_limit_reraises_other_errors(monkeypatch):
    fake = FakeDb(RuntimeError("connection lost"))
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    with pytest.raises(RuntimeError):
        rate_limit.check_generation_rate_limit(user_id="user-1")


def test_rate_limit_window_start_is_aligned(monkeypatch):
    fake = FakeDb()
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    rate_limit.check_generation_rate_limit(user_id="user-1", limit=3, window_seconds=60)
    window_start = fake.calls[0][1]["p_window_started_at"]
    assert window_start.second == 0 and window_start.microsecond == 0
