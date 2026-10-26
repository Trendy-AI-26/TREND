"""Admin-disabled accounts are refused at login and on every authenticated
request; tokens of deleted (missing) users are refused as invalid."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.core import security
from app.core.auth import get_current_user
from app.core.security import SESSION_COOKIE_NAME, create_session_token
from app.main import app
from app.repositories import users
# Bound at import time, before the autouse conftest stub replaces the attribute.
from app.repositories.users import account_status as real_account_status
from app.routers import auth as auth_router
from app.services import auth_service

USER_ID = "7b1f2f4e-8d6a-4c53-9a3e-0d3b6f5a9c11"
EMAIL = "person@example.com"
PASSWORD = "correct horse battery"


class OneUserRepo:
    """Just enough of app.repositories.users for login."""

    def __init__(self, user):
        self.user = user
        self.codes_issued = 0

    def get_user_by_email(self, email):
        return self.user if email.lower() == self.user["email"] else None

    def issue_code_if_allowed(self, *args, **kwargs):
        self.codes_issued += 1
        return "issued"


def _user(**overrides):
    user = {
        "id": USER_ID,
        "email": EMAIL,
        "password_hash": security.hash_password(PASSWORD),
        "email_verified_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "disabled_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "full_name": "Test Person",
    }
    user.update(overrides)
    return user


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    async def fake_send(to, code, purpose):
        sent.append((to, purpose))

    monkeypatch.setattr(auth_router, "send_code_email", fake_send)
    return sent


# -------------------------------------------------------------------- login


def test_login_refuses_disabled_account(monkeypatch):
    monkeypatch.setattr(auth_service, "users_repo", OneUserRepo(_user()))

    with pytest.raises(auth_service.AuthError) as error:
        auth_service.login(EMAIL, PASSWORD)

    assert (error.value.status_code, error.value.code) == (403, "ACCOUNT_DISABLED")


def test_disabled_account_with_wrong_password_looks_like_any_bad_login(monkeypatch):
    monkeypatch.setattr(auth_service, "users_repo", OneUserRepo(_user()))

    with pytest.raises(auth_service.AuthError) as error:
        auth_service.login(EMAIL, "wrong password")

    assert (error.value.status_code, error.value.code) == (401, "INVALID_CREDENTIALS")


def test_disabled_unverified_account_gets_no_code(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", True)
    repo = OneUserRepo(_user(email_verified_at=None))
    monkeypatch.setattr(auth_service, "users_repo", repo)

    with pytest.raises(auth_service.AuthError) as error:
        auth_service.login(EMAIL, PASSWORD)

    assert error.value.code == "ACCOUNT_DISABLED"
    assert error.value.pending_email is None
    assert repo.codes_issued == 0


def test_enabled_account_still_logs_in(monkeypatch):
    monkeypatch.setattr(auth_service, "users_repo", OneUserRepo(_user(disabled_at=None)))

    assert auth_service.login(EMAIL, PASSWORD)["id"] == USER_ID


def test_login_endpoint_returns_403_without_a_session_cookie(monkeypatch, outbox):
    monkeypatch.setattr(auth_service, "users_repo", OneUserRepo(_user()))

    response = TestClient(app).post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"
    assert SESSION_COOKIE_NAME not in response.cookies
    assert outbox == []


# ---------------------------------------------------- authenticated requests


def _status(monkeypatch, value):
    """Stub the per-request lookup; returns the list of looked-up user ids."""
    seen = []
    monkeypatch.setattr(users, "account_status", lambda user_id: seen.append(user_id) or value)
    return seen


def _call_get_current_user(token):
    return get_current_user(
        request=SimpleNamespace(cookies={}),
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
    )


def test_get_current_user_rejects_disabled_account(monkeypatch):
    seen = _status(monkeypatch, "disabled")

    with pytest.raises(HTTPException) as error:
        _call_get_current_user(create_session_token(USER_ID, EMAIL))

    assert error.value.status_code == 403
    assert error.value.detail["error"]["code"] == "ACCOUNT_DISABLED"
    assert "request_id" in error.value.detail["error"]
    assert seen == [USER_ID]


def test_get_current_user_rejects_token_of_a_missing_user(monkeypatch):
    seen = _status(monkeypatch, "missing")

    with pytest.raises(HTTPException) as error:
        _call_get_current_user(create_session_token(USER_ID, EMAIL))

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"
    assert "request_id" in error.value.detail["error"]
    assert error.value.headers == {"WWW-Authenticate": "Bearer"}
    assert seen == [USER_ID]


def test_get_current_user_accepts_active_account(monkeypatch):
    seen = _status(monkeypatch, "active")
    token = create_session_token(USER_ID, EMAIL)

    user = _call_get_current_user(token)

    assert (user.id, user.email, user.access_token) == (USER_ID, EMAIL, token)
    assert seen == [USER_ID]  # exactly one lookup


@pytest.mark.parametrize(
    ("account", "status_code", "code"),
    [("disabled", 403, "ACCOUNT_DISABLED"), ("missing", 401, "INVALID_TOKEN")],
)
@pytest.mark.parametrize("path", ["/auth/session", "/brands"])
def test_blocked_accounts_on_authenticated_requests(monkeypatch, path, account, status_code, code):
    _status(monkeypatch, account)
    token = create_session_token(USER_ID, EMAIL)

    bearer = TestClient(app).get(path, headers={"Authorization": f"Bearer {token}"})
    cookie = TestClient(app, cookies={SESSION_COOKIE_NAME: token}).get(path)

    for response in (bearer, cookie):
        assert response.status_code == status_code
        assert response.json()["error"]["code"] == code
        if status_code == 401:
            assert response.headers["www-authenticate"] == "Bearer"


def test_deleted_users_token_stops_working(monkeypatch):
    """A token issued before DELETE /admin/users/{id} is refused afterwards."""
    monkeypatch.setattr(db, "fetch_all", lambda *a, **k: [])
    token = create_session_token(USER_ID, EMAIL)
    client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

    _status(monkeypatch, "active")
    assert client.get("/brands").status_code == 200

    _status(monkeypatch, "missing")
    response = client.get("/brands")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_active_account_passes_the_check(monkeypatch):
    _status(monkeypatch, "active")
    monkeypatch.setattr(db, "fetch_all", lambda *a, **k: [])
    token = create_session_token(USER_ID, EMAIL)

    response = TestClient(app).get("/brands", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


# ------------------------------------------------------------ repository


@pytest.mark.parametrize(
    ("row", "expected"),
    [({"disabled": True}, "disabled"), ({"disabled": False}, "active"), (None, "missing")],
)
def test_account_status_is_one_primary_key_lookup(monkeypatch, row, expected):
    calls = []

    def fake_fetch_one(sql, params=None, *, raw=False):
        calls.append((" ".join(sql.split()), params))
        return row

    monkeypatch.setattr(db, "fetch_one", fake_fetch_one)

    assert real_account_status(USER_ID) == expected
    ((sql, params),) = calls
    assert "FROM users WHERE id = CAST(:user_id AS uuid)" in sql
    assert params == {"user_id": USER_ID}


@pytest.mark.parametrize("user_id", ["user-123", "", "not a uuid"])
def test_account_status_of_a_non_uuid_id_is_missing_without_a_query(monkeypatch, user_id):
    def fail(*args, **kwargs):
        raise AssertionError("no query expected")

    monkeypatch.setattr(db, "fetch_one", fail)

    assert real_account_status(user_id) == "missing"
