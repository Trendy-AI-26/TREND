from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.core.auth import get_current_user
from app.core.security import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    SESSION_COOKIE_NAME,
    create_reset_token,
    create_session_token,
)
from app.main import app
from app.routers import generations

USER_ID = "7b1f2f4e-8d6a-4c53-9a3e-0d3b6f5a9c11"
EMAIL = "user@example.com"


def _request(cookie: str | None = None):
    cookies = {SESSION_COOKIE_NAME: cookie} if cookie else {}
    return SimpleNamespace(cookies=cookies)


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _forge(claims: dict, secret: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        **claims,
    }
    return jwt.encode(payload, secret or settings.AUTH_JWT_SECRET, algorithm="HS256")


# For missing credentials:


def test_get_current_user_rejects_missing_credentials():
    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=None)

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "request_id" in error.value.detail["error"]


# Token not valid:


def test_get_current_user_rejects_invalid_token():
    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer("invalid-token"))

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"
    assert "request_id" in error.value.detail["error"]


def test_get_current_user_accepts_valid_bearer_token():
    token = create_session_token(USER_ID, EMAIL)

    user = get_current_user(request=_request(), credentials=_bearer(token))

    assert user.id == USER_ID
    assert user.email == EMAIL
    assert user.access_token == token


def test_get_current_user_accepts_session_cookie():
    token = create_session_token(USER_ID, EMAIL)

    user = get_current_user(request=_request(cookie=token), credentials=None)

    assert user.id == USER_ID
    assert user.email == EMAIL
    assert user.access_token == token


def test_cookie_takes_precedence_over_bearer_header():
    cookie_token = create_session_token(USER_ID, EMAIL)
    other_token = create_session_token("00000000-0000-0000-0000-000000000009", "x@example.com")

    user = get_current_user(request=_request(cookie=cookie_token), credentials=_bearer(other_token))

    assert user.id == USER_ID


def test_session_token_claims_follow_the_contract():
    token = create_session_token(USER_ID, EMAIL)
    claims = jwt.decode(
        token,
        settings.AUTH_JWT_SECRET,
        algorithms=["HS256"],
        audience="trendy",
    )

    assert claims["sub"] == USER_ID
    assert claims["email"] == EMAIL
    assert claims["iss"] == "trendy-api"
    assert claims["aud"] == "trendy"
    assert claims["exp"] - claims["iat"] == settings.AUTH_SESSION_TTL_SECONDS


# Token with incomplete data:
def test_get_current_user_rejects_token_without_subject():
    token = _forge({"email": EMAIL})

    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer(token))

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


def test_get_current_user_rejects_token_without_email():
    token = _forge({"sub": USER_ID})

    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer(token))

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(
            _forge({"sub": USER_ID, "email": EMAIL}, secret="x" * 40),
            id="wrong-secret",
        ),
        pytest.param(
            _forge({"sub": USER_ID, "email": EMAIL, "exp": 1}),
            id="expired",
        ),
        pytest.param(
            _forge({"sub": USER_ID, "email": EMAIL, "aud": "authenticated"}),
            id="wrong-audience",
        ),
        pytest.param(
            _forge({"sub": USER_ID, "email": EMAIL, "iss": "someone-else"}),
            id="wrong-issuer",
        ),
    ],
)
def test_get_current_user_rejects_untrusted_tokens(token):
    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer(token))

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


def test_reset_token_cannot_be_used_as_a_session():
    token = create_reset_token(USER_ID, EMAIL, "bcrypt-hash")

    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer(token))

    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


def test_unsigned_none_algorithm_token_is_rejected():
    now = int(datetime.now(timezone.utc).timestamp())
    token = jwt.encode(
        {
            "sub": USER_ID,
            "email": EMAIL,
            "iat": now,
            "exp": now + 3600,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        key=None,
        algorithm="none",
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(request=_request(), credentials=_bearer(token))

    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


# Protected endpoints through the real app:

client = TestClient(app)


@pytest.fixture
def no_brands(monkeypatch):
    monkeypatch.setattr(db, "fetch_all", lambda *a, **k: [])


def test_protected_endpoint_requires_authentication():
    response = client.get("/brands")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_protected_endpoint_accepts_cookie_auth(no_brands):
    token = create_session_token(USER_ID, EMAIL)

    response = TestClient(app, cookies={SESSION_COOKIE_NAME: token}).get("/brands")

    assert response.status_code == 200
    assert response.json() == []


def test_protected_endpoint_accepts_bearer_auth(no_brands):
    token = create_session_token(USER_ID, EMAIL)

    response = client.get("/brands", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == []


def test_protected_endpoint_rejects_garbage_bearer():
    response = client.get("/brands", headers={"Authorization": "Bearer nope"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_admin_endpoint_rejects_non_admin_session():
    token = create_session_token(USER_ID, EMAIL)

    response = client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# Test Authorization:
def test_user_cannot_access_another_users_brand(monkeypatch):
    def reject_wrong_owner(*args, **kwargs):
        raise generations._error_response(
            404,
            "BRAND_NOT_FOUND",
            "Brand not found",
        )

    monkeypatch.setattr(
        generations,
        "_get_brand_or_404",
        reject_wrong_owner,
    )

    with pytest.raises(HTTPException) as error:
        generations._get_brand_or_404("brand", "user")

    assert error.value.status_code == 404
    assert error.value.detail["error"]["code"] == "BRAND_NOT_FOUND"
