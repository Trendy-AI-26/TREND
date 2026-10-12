from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.core.auth import User
from app.routers import brands
from app.services import quota


class FakeRpc:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=self.response)


class FakeClient:
    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRpc(self.responses.get(name), self.error)


def test_reserve_generation_slot_uses_atomic_rpc(monkeypatch):
    client = FakeClient(responses={"reserve_generation_slot": {"status": "reserved"}})
    monkeypatch.setattr(quota, "get_service_client", lambda: client)
    generation_id = uuid4()

    quota.reserve_generation_slot(user_id="user-1", generation_id=generation_id)

    assert client.calls == [
        (
            "reserve_generation_slot",
            {"p_user_id": "user-1", "p_generation_id": str(generation_id)},
        )
    ]


def test_generation_limit_error_is_stable(monkeypatch):
    client = FakeClient(error=Exception("GENERATION_LIMIT_REACHED"))
    monkeypatch.setattr(quota, "get_service_client", lambda: client)

    with pytest.raises(quota.QuotaError) as error:
        quota.reserve_generation_slot(user_id="user-1", generation_id=uuid4())

    assert error.value.code == "GENERATION_LIMIT_REACHED"


def test_commit_and_release_are_separate_idempotent_rpc_operations(monkeypatch):
    client = FakeClient(
        responses={
            "commit_generation_slot": {"status": "committed"},
            "release_generation_slot": {"status": "released"},
        }
    )
    monkeypatch.setattr(quota, "get_service_client", lambda: client)
    generation_id = uuid4()

    quota.commit_generation_slot(user_id="user-1", generation_id=generation_id)
    quota.release_generation_slot(user_id="user-1", generation_id=generation_id)

    assert [call[0] for call in client.calls] == [
        "commit_generation_slot",
        "release_generation_slot",
    ]


def test_quota_summary_maps_rpc_response(monkeypatch):
    client = FakeClient(
        responses={
            "get_generation_quota_summary": {
                "plan": "beta",
                "max_active_brands": 3,
                "active_brands": 2,
                "generation_limit": 15,
                "generation_reserved": 1,
                "generation_consumed": 8,
                "generation_remaining": 6,
            }
        }
    )
    monkeypatch.setattr(quota, "get_service_client", lambda: client)

    summary = quota.get_quota_summary(user_id="user-1")

    assert summary.max_active_brands == 3
    assert summary.generation_remaining == 6


@pytest.mark.asyncio
async def test_create_brand_returns_limit_error(monkeypatch):
    async def fake_kit_status(_brand_id):
        return "not_started"

    monkeypatch.setattr(brands, "_get_kit_status", fake_kit_status)
    monkeypatch.setattr(
        brands,
        "create_brand_if_allowed",
        lambda **_: (_ for _ in ()).throw(
            quota.QuotaError(
                "BRAND_LIMIT_REACHED",
                "You can have up to 3 active brands on the free plan.",
            )
        ),
    )

    with pytest.raises(Exception) as error:
        await brands.create_brand(
            brands.CreateBrandRequest(name="Fourth Brand"),
            User(id="user-1", email="user@example.com", access_token="token"),
        )

    assert getattr(error.value, "status_code", None) == 403
    assert error.value.detail["error"]["code"] == "BRAND_LIMIT_REACHED"

def test_trial_and_daily_quota_errors_are_stable(monkeypatch):
    client = FakeClient(error=Exception("DAILY_GENERATION_LIMIT_REACHED"))
    monkeypatch.setattr(quota, "get_service_client", lambda: client)
    with pytest.raises(quota.QuotaError) as error:
        quota.reserve_generation_slot(user_id="user-1", generation_id=uuid4())
    assert error.value.code == "DAILY_GENERATION_LIMIT_REACHED"
    assert "3" in error.value.message


def test_quota_summary_includes_trial_and_daily_fields(monkeypatch):
    client = FakeClient(
        responses={
            "get_generation_quota_summary": {
                "plan": "beta",
                "max_active_brands": 3,
                "active_brands": 1,
                "generation_limit": 42,
                "generation_reserved": 0,
                "generation_consumed": 4,
                "generation_remaining": 38,
                "daily_generation_limit": 3,
                "daily_generation_reserved": 1,
                "daily_generation_consumed": 2,
                "daily_generation_remaining": 0,
                "trial_ends_at": "2026-10-26T00:00:00+00:00",
                "trial_active": True,
            }
        }
    )
    monkeypatch.setattr(quota, "get_service_client", lambda: client)
    summary = quota.get_quota_summary(user_id="user-1")
    assert summary.daily_generation_remaining == 0
    assert summary.daily_generation_consumed == 2
    assert summary.trial_active is True
