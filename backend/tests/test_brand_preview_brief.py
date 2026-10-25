from uuid import uuid4

from fastapi.testclient import TestClient

from app import db
from app.core.auth import User
from app.main import app
from app.routers import brands as brands_router


def _valid_payload() -> dict:
    return {
        "brief": {
            "campaign_goal": "brand_awareness",
            "content_type": "product_showcase",
            "target_audience": {
                "segments": ["entrepreneurs"],
                "location": "UAE",
                "age_range": "25_34",
                "gender_focus": "women",
                "details": "tech-savvy shoppers",
            },
            "core_idea": "Show our premium coffee experience",
            "voice_tone": "friendly",
            "optional_notes": "Clean and premium",
            "text_to_include": "Freshly brewed",
        },
        "platform_preset": "instagram_post",
    }


def _install_user(user_id: str = "user-123") -> None:
    app.dependency_overrides[brands_router.get_current_user] = lambda: User(
        id=user_id,
        email="user@example.com",
        access_token="test-token",
    )


def test_preview_brand_brief_returns_creative_direction(monkeypatch):
    brand_id = str(uuid4())
    fake_brand = {
        "id": brand_id,
        "name": "Acme",
        "logo_path": None,
        "updated_at": "2024-01-01T00:00:00Z",
    }

    def fake_fetch_one(sql, params=None, **_kwargs):
        return fake_brand if "FROM brands" in sql else None

    monkeypatch.setattr(db, "fetch_one", fake_fetch_one)
    _install_user()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/brands/{brand_id}/preview-brief",
                json={"brief": {}},
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(brands_router.get_current_user, None)


def test_preview_brand_brief_rejects_non_object_brief(monkeypatch):
    brand_id = str(uuid4())
    monkeypatch.setattr(
        brands_router,
        "_get_brand_or_404",
        lambda _brand_id, _user_id: {"id": brand_id, "name": "Acme"},
    )
    _install_user()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/brands/{brand_id}/preview-brief",
                json={"brief": "not-an-object", "platform_preset": "instagram_post"},
            )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(brands_router.get_current_user, None)


def test_preview_brand_brief_enforces_brand_ownership(monkeypatch):
    brand_id = str(uuid4())
    owner_id = "brand-owner"

    seen_params = []

    def fake_fetch_one(sql, params=None, **_kwargs):
        # Ownership must be part of the brand query itself.
        assert "owner_user_id" in sql
        seen_params.append(dict(params))
        if params["user_id"] == owner_id:
            return {"id": brand_id, "name": "Owned Brand"}
        return None

    monkeypatch.setattr(db, "fetch_one", fake_fetch_one)
    _install_user("different-user")

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/brands/{brand_id}/preview-brief", json=_valid_payload()
            )

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "BRAND_NOT_FOUND"
        assert seen_params == [{"brand_id": brand_id, "user_id": "different-user"}]
    finally:
        app.dependency_overrides.pop(brands_router.get_current_user, None)


def test_preview_brand_brief_accepts_english_language(monkeypatch):
    brand_id = str(uuid4())
    monkeypatch.setattr(
        brands_router,
        "_get_brand_or_404",
        lambda _brand_id, _user_id: {"id": brand_id, "name": "Acme"},
    )
    _install_user()
    payload = _valid_payload()
    payload["brief"]["language"] = "en"

    try:
        with TestClient(app) as client:
            response = client.post(f"/brands/{brand_id}/preview-brief", json=payload)

        assert response.status_code == 200
        assert response.json()["language"] == "en"
    finally:
        app.dependency_overrides.pop(brands_router.get_current_user, None)


def test_preview_brand_brief_rejects_unsupported_language(monkeypatch):
    brand_id = str(uuid4())
    monkeypatch.setattr(
        brands_router,
        "_get_brand_or_404",
        lambda _brand_id, _user_id: {"id": brand_id, "name": "Acme"},
    )
    _install_user()
    payload = _valid_payload()
    payload["brief"]["language"] = "Arabic"

    try:
        with TestClient(app) as client:
            response = client.post(f"/brands/{brand_id}/preview-brief", json=payload)

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert "language" in response.json()["error"]["message"]
    finally:
        app.dependency_overrides.pop(brands_router.get_current_user, None)
