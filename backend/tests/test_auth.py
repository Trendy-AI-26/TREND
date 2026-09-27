from app.routers import generations
from fastapi import HTTPException
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from types import SimpleNamespace
from app.core.auth import get_current_user
from app.core.auth import get_current_user
from fastapi.testclient import TestClient
from app.main import app
from jwt.exceptions import PyJWKClientError


# For missing credentials:

def test_get_current_user_rejects_missing_credentials():
    with pytest.raises(HTTPException) as error:
        get_current_user(credentials=None)

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "request_id" in error.value.detail["error"]

# Token not valid:

def test_get_current_user_rejects_invalid_token(monkeypatch):
    def fail_to_get_signing_key(_token):
        raise PyJWKClientError("Invalid signing key")

    monkeypatch.setattr(
        "app.core.auth._jwks_client.get_signing_key_from_jwt",
        fail_to_get_signing_key,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(credentials=credentials)

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


# Test Valid token without real token:

def test_get_current_user_accepts_valid_token(monkeypatch):
    monkeypatch.setattr(
        "app.core.auth._jwks_client.get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key="fake-signing-key"),
    )

    monkeypatch.setattr(
        "app.core.auth.jwt.decode",
        lambda token, key, algorithms, audience: {
            "sub": "user-123",
            "email": "user@example.com",
        },
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-valid-token",
    )

    user = get_current_user(credentials=credentials)

    assert user.id == "user-123"
    assert user.email == "user@example.com"
    assert user.access_token == "fake-valid-token"

# Token with unfull data:
# Without Sub:
def test_get_current_user_rejects_token_without_subject(monkeypatch):
    monkeypatch.setattr(
        "app.core.auth._jwks_client.get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key="fake-signing-key"),
    )

    monkeypatch.setattr(
        "app.core.auth.jwt.decode",
        lambda *args, **kwargs: {
            "email": "user@example.com",
        },
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(credentials=credentials)

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"

# Without Email:
def test_get_current_user_rejects_token_without_email(monkeypatch):
    monkeypatch.setattr(
        "app.core.auth._jwks_client.get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key="fake-signing-key"),
    )

    monkeypatch.setattr(
        "app.core.auth.jwt.decode",
        lambda *args, **kwargs: {
            "sub": "user-123",
        },
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    with pytest.raises(HTTPException) as error:
        get_current_user(credentials=credentials)

    assert error.value.status_code == 401
    assert error.value.detail["error"]["code"] == "INVALID_TOKEN"


client = TestClient(app)
# Request without token:
def test_protected_endpoint_requires_authentication():
    response = client.get("/brands")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

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

   
