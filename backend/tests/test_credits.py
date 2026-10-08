from uuid import uuid4

import pytest

from app.services import credits


class FakeRpc:
    def __init__(self):
        self.calls = []

    def execute(self):
        return type("Response", (), {"data": {}})()


class FakeClient:
    def __init__(self):
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return FakeRpc()


def test_reserve_calls_atomic_rpc(monkeypatch):
    fake = FakeClient()

    monkeypatch.setattr(
        credits,
        "get_service_client",
        lambda: fake,
    )

    generation_id = uuid4()

    reservation = credits.reserve_credits(
        user_id="user-1",
        generation_id=generation_id,
        amount=1,
        idempotency_key="reserve-key-123456",
    )

    assert reservation.amount == 1
    assert fake.calls[0][0] == (
        "reserve_generation_credit"
    )
    assert fake.calls[0][1]["p_user_id"] == "user-1"


def test_insufficient_credits_is_mapped(monkeypatch):
    class FailingRpc:
        def execute(self):
            raise Exception("INSUFFICIENT_CREDITS")

    class FailingClient:
        def rpc(self, *_args, **_kwargs):
            return FailingRpc()

    monkeypatch.setattr(
        credits,
        "get_service_client",
        lambda: FailingClient(),
    )

    with pytest.raises(credits.CreditsError) as error:
        credits.reserve_credits(
            user_id="user-1",
            generation_id=uuid4(),
            amount=1,
            idempotency_key="reserve-key-abcdef",
        )

    assert error.value.code == "INSUFFICIENT_CREDITS"

