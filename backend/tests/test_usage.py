import json
from uuid import uuid4

import pytest

from app import db
from app.services import usage


class FakeDb:
    def __init__(self):
        self.inserted = []
        self.updated = []

    def fetch_one(self, sql, params=None, **_kwargs):
        assert "INSERT INTO usage_events" in sql
        self.inserted.append(params)
        return {"id": "usage-1"}

    def execute(self, sql, params=None):
        assert "UPDATE usage_events" in sql
        self.updated.append(params)
        return 1


def test_usage_timer_records_success(monkeypatch):
    fake = FakeDb()
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    monkeypatch.setattr(db, "execute", fake.execute)

    timer = usage.UsageTimer(
        user_id="user-1",
        generation_id=uuid4(),
        feature="image_generation",
        provider="openai",
        model="gpt-image-2",
        credits=1,
    )

    timer.start()
    timer.finish(
        status="succeeded",
        provider_request_id="request-1",
    )

    assert len(fake.inserted) == 1
    assert fake.inserted[0]["feature"] == "image_generation"
    assert fake.inserted[0]["credits"] == 1

    assert timer.usage_id == "usage-1"
    assert len(fake.updated) == 1
    assert fake.updated[0]["status"] == "succeeded"
    assert fake.updated[0]["provider_request_id"] == "request-1"
    assert fake.updated[0]["usage_id"] == "usage-1"
    assert json.loads(fake.updated[0]["metadata"]) == {}


def test_finish_usage_rejects_unknown_status():
    with pytest.raises(ValueError):
        usage.finish_usage(usage_id="u", status="started", duration_ms=1)
