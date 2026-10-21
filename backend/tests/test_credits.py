from uuid import uuid4

import pytest

from app import db
from app.services import credits


class FakeDb:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = {} if result is None else result
        self.error = error

    def fetch_one(self, sql, params=None, **_kwargs):
        self.calls.append((sql, params))
        if self.error:
            raise self.error
        return {"result": self.result}


def test_reserve_calls_atomic_function(monkeypatch):
    fake = FakeDb()
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)

    generation_id = uuid4()

    reservation = credits.reserve_credits(
        user_id="user-1",
        generation_id=generation_id,
        amount=1,
        idempotency_key="reserve-key-123456",
    )

    assert reservation.amount == 1
    assert reservation.reservation_id == "reserve-key-123456"
    sql, params = fake.calls[0]
    assert "reserve_generation_credit" in sql
    assert params["p_user_id"] == "user-1"
    assert params["p_generation_id"] == str(generation_id)


def test_insufficient_credits_is_mapped(monkeypatch):
    fake = FakeDb(error=Exception("INSUFFICIENT_CREDITS"))
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)

    with pytest.raises(credits.CreditsError) as error:
        credits.reserve_credits(
            user_id="user-1",
            generation_id=uuid4(),
            amount=1,
            idempotency_key="reserve-key-abcdef",
        )

    assert error.value.code == "INSUFFICIENT_CREDITS"


def test_commit_and_release_call_their_functions(monkeypatch):
    fake = FakeDb({"status": "ok"})
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)
    reservation = credits.CreditReservation(
        reservation_id="res-1", user_id="user-1", generation_id=str(uuid4()), amount=1
    )

    credits.commit_credits(reservation)
    credits.release_credits(reservation)

    assert "commit_generation_credit" in fake.calls[0][0]
    assert "release_generation_credit" in fake.calls[1][0]
    assert fake.calls[1][1]["p_reservation_id"] == "res-1"


def test_available_credits_reads_integer_result(monkeypatch):
    fake = FakeDb(7)
    monkeypatch.setattr(db, "fetch_one", fake.fetch_one)

    assert credits.get_available_credits("user-1") == 7
    assert "get_available_credits" in fake.calls[0][0]
