"""Admin API end to end through the real app, with an in-memory admin repository."""

import copy
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.core import storage
from app.core.security import create_session_token
from app.main import app
from app.repositories import admin as real_admin_repo
from app.routers import admin as admin_router

ADMIN_ID = "11111111-1111-4111-8111-111111111111"
ADMIN_EMAIL = "admin@example.com"
OTHER_ADMIN_ID = "22222222-2222-4222-8222-222222222222"
OTHER_ADMIN_EMAIL = "boss@example.com"
USER_ID = "33333333-3333-4333-8333-333333333333"
USER_EMAIL = "user@example.com"
BRAND_ID = "44444444-4444-4444-8444-444444444444"
GEN_ID = "55555555-5555-4555-8555-555555555555"
TREND_ID = "66666666-6666-4666-8666-666666666666"
UNKNOWN_ID = "99999999-9999-4999-8999-999999999999"


class _PgError(Exception):
    def __init__(self, sqlstate: str, message: str = "db error") -> None:
        super().__init__(message)
        self.sqlstate = sqlstate


def _integrity_error(sqlstate: str) -> db.IntegrityError:
    return db.IntegrityError("SQL", {}, _PgError(sqlstate))


def user_row(user_id=USER_ID, email=USER_EMAIL, **overrides):
    row = {
        "id": user_id,
        "email": email,
        "full_name": "Test Person",
        "email_verified_at": None,
        "disabled_at": None,
        "created_at": "2026-06-01T09:00:00+00:00",
        "trial_ends_at": "2026-06-15T09:00:00+00:00",
        "brands_count": 2,
        "generations_count": 5,
        "generations_succeeded": 3,
        "quota_limit": 42,
        "quota_consumed": 3,
        "quota_reserved": 1,
        "credits_balance": 39,
        "credits_reserved": 1,
        "today_limit": 3,
        "today_consumed": 2,
        "today_reserved": 1,
    }
    row.update(overrides)
    return row


def generation_row(**overrides):
    row = {
        "id": GEN_ID,
        "status": "failed",
        "provider": "openai",
        "model": "gpt-image-2",
        "platform_preset": "instagram_post",
        "error_code": "PROVIDER_ERROR",
        "error_message": "boom",
        "created_at": "2026-06-19T12:00:00+00:00",
        "completed_at": "2026-06-19T12:00:05+00:00",
        "image_path": None,
        "needs_review": False,
        "brand_id": BRAND_ID,
        "brand_name": "Acme",
        "user_id": USER_ID,
        "user_email": USER_EMAIL,
    }
    row.update(overrides)
    return row


def trend_row(**overrides):
    row = {
        "id": TREND_ID,
        "name": "Soft Pastels",
        "slug": "soft-pastels",
        "description": None,
        "category": "visual",
        "industry": ["food"],
        "region": [],
        "platform": ["instagram"],
        "audience": [],
        "visual_style": ["pastel"],
        "content_patterns": [],
        "keywords": ["calm", 7],
        "avoid_patterns": [],
        "popularity_score": 50,
        "growth_score": 40,
        "relevance_score": 30,
        "status": "active",
        "source": "manual",
        "observed_at": None,
        "expires_at": None,
        "created_at": "2026-06-01T09:00:00+00:00",
        "updated_at": "2026-06-01T09:00:00+00:00",
    }
    row.update(overrides)
    return row


class FakeAdminRepo:
    """Mirrors app.repositories.admin on plain dicts and records every call."""

    TREND_JSON_FIELDS = real_admin_repo.TREND_JSON_FIELDS

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.audit: list[dict] = []
        self.users = {
            USER_ID: user_row(),
            ADMIN_ID: user_row(ADMIN_ID, ADMIN_EMAIL),
            OTHER_ADMIN_ID: user_row(OTHER_ADMIN_ID, OTHER_ADMIN_EMAIL),
        }
        self.ledger: dict[str, list[dict]] = {USER_ID: []}
        self.trends = {TREND_ID: trend_row()}
        self.trend_in_use = False
        self.stats = {
            "total_accounts": 3, "total_brands": 2, "total_generations": 5,
            "generations_pending": 1, "generations_processing": 0,
            "generations_succeeded": 3, "generations_failed": 1,
            "generations_openai": 5, "generations_gemini": 0,
            "generations_last_7d": 4, "generations_last_30d": 5,
            "brand_kits_complete": 1, "active_provider_keys": 0,
        }
        self.overview_counts = {
            "users_total": 3, "users_verified": 2, "users_new_7d": 1, "users_disabled": 1,
            "brands_total": 2, "brands_kits_complete": 1,
            "generations_total": 5, "generations_today": 1, "generations_last_7d": 4,
            "generations_last_30d": 5, "generations_succeeded": 3, "generations_failed": 1,
            "generations_pending": 1, "generations_processing": 0,
            "generations_succeeded_30d": 3, "generations_failed_30d": 1,
            "credits_charged_30d": 3, "estimated_provider_cost_30d": 0.12,
        }
        self.daily = [
            {"date": "2026-06-10", "succeeded": 1, "failed": 0},
            {"date": "2026-06-19", "succeeded": 2, "failed": 1},
        ]
        self.brands = [
            {
                "id": BRAND_ID, "name": "Acme", "owner_id": USER_ID,
                "owner_email": USER_EMAIL, "owner_full_name": "Test Person",
                "kit_status": "complete", "colors_count": 4, "has_logo": True,
                "generation_count": 5, "created_at": "2026-06-02T09:00:00+00:00",
            }
        ]
        self.generations = [
            generation_row(),
            generation_row(
                id=str(uuid.uuid4()), status="succeeded", error_code=None, error_message=None,
                image_path=f"brands/{BRAND_ID}/generations/{GEN_ID}.png",
            ),
        ]
        self.delete_files = {
            "email": USER_EMAIL,
            "brand_files": [f"brands/{BRAND_ID}/logo.png", f"brands/{BRAND_ID}/generations/{GEN_ID}.png"],
            "product_asset_files": [f"brands/{BRAND_ID}/product-assets/{GEN_ID}.png"],
            "avatar_files": [f"avatars/{USER_ID}/avatar.png"],
        }

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))

    @staticmethod
    def _page(rows, offset, limit):
        return [copy.deepcopy(r) for r in rows[offset : offset + limit]], len(rows)

    # monitoring
    def get_stats(self):
        self._record("get_stats")
        return dict(self.stats)

    def get_overview_counts(self):
        self._record("get_overview_counts")
        return dict(self.overview_counts)

    def get_daily_outcomes(self, days=30):
        self._record("get_daily_outcomes", days=days)
        return list(self.daily)

    def list_needs_review(self, limit=20):
        self._record("list_needs_review", limit=limit)
        return [generation_row(status="processing", error_code=None, error_message=None,
                               completed_at=None, needs_review=True)]

    def list_recent_failures(self, limit=10):
        self._record("list_recent_failures", limit=limit)
        return [generation_row()]

    # users
    def list_users(self, **kwargs):
        self._record("list_users", **kwargs)
        return self._page(list(self.users.values()), kwargs["offset"], kwargs["limit"])

    def get_user(self, user_id):
        self._record("get_user", user_id=user_id)
        row = self.users.get(user_id)
        return copy.deepcopy(row) if row else None

    def get_user_target(self, user_id):
        self._record("get_user_target", user_id=user_id)
        row = self.users.get(user_id)
        return {"id": row["id"], "email": row["email"]} if row else None

    def list_user_brands(self, user_id):
        self._record("list_user_brands", user_id=user_id)
        return [{"id": BRAND_ID, "name": "Acme", "kit_status": "complete",
                 "generation_count": 5, "created_at": "2026-06-02T09:00:00+00:00"}]

    def list_user_generations(self, user_id, limit=10):
        self._record("list_user_generations", user_id=user_id, limit=limit)
        return [generation_row()]

    def list_user_ledger(self, user_id, limit=20):
        self._record("list_user_ledger", user_id=user_id, limit=limit)
        return list(self.ledger.get(user_id, []))[:limit]

    def _action(self, name, user_id, audit, **kwargs):
        self._record(name, user_id=user_id, audit=audit, **kwargs)
        if user_id not in self.users:
            return None
        self.audit.append(audit)
        return self.users[user_id]

    def verify_user_email(self, user_id, audit):
        row = self._action("verify_user_email", user_id, audit)
        if row is not None:
            row["email_verified_at"] = row["email_verified_at"] or "2026-06-20T10:00:00+00:00"
        return row

    def set_user_disabled(self, user_id, disabled, audit):
        row = self._action("set_user_disabled", user_id, audit, disabled=disabled)
        if row is not None:
            row["disabled_at"] = "2026-06-20T10:00:00+00:00" if disabled else None
        return row

    def grant_generations(self, user_id, *, generations, credits, idempotency_key, metadata, audit):
        row = self._action(
            "grant_generations", user_id, audit, generations=generations, credits=credits,
            idempotency_key=idempotency_key, metadata=metadata,
        )
        if row is None:
            return None
        row["quota_limit"] += generations
        row["credits_balance"] += credits
        self.ledger.setdefault(user_id, []).insert(0, {
            "id": str(uuid.uuid4()), "operation": "grant", "amount": credits,
            "metadata": {**metadata, "generations": generations, "credits": credits},
            "created_at": "2026-06-20T10:00:00+00:00",
        })
        return {"generation_limit": row["quota_limit"], "credit_balance": row["credits_balance"]}

    def extend_trial(self, user_id, days, audit):
        row = self._action("extend_trial", user_id, audit, days=days)
        if row is not None:
            row["trial_ends_at"] = "2026-07-15T09:00:00+00:00"
        return row

    def reset_daily_usage(self, user_id, audit):
        row = self._action("reset_daily_usage", user_id, audit)
        if row is not None:
            row["today_consumed"] = 0
        return row

    def delete_user(self, user_id, audit):
        self._record("delete_user", user_id=user_id, audit=audit)
        if self.users.pop(user_id, None) is None:
            return None
        self.audit.append(audit)
        return copy.deepcopy(self.delete_files)

    # brands / generations
    def list_brands(self, **kwargs):
        self._record("list_brands", **kwargs)
        return self._page(self.brands, kwargs["offset"], kwargs["limit"])

    def list_generations(self, **kwargs):
        self._record("list_generations", **kwargs)
        return self._page(self.generations, kwargs["offset"], kwargs["limit"])

    # trends
    def list_trends(self, **kwargs):
        self._record("list_trends", **kwargs)
        return self._page(list(self.trends.values()), kwargs["offset"], kwargs["limit"])

    def create_trend(self, values, audit):
        self._record("create_trend", values=values, audit=audit)
        if any(t["slug"] == values["slug"] for t in self.trends.values()):
            raise _integrity_error("23505")
        new_id = str(uuid.uuid4())
        row = trend_row(
            id=new_id,
            **{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in values.items()},
        )
        self.trends[new_id] = row
        self.audit.append({**audit, "target_id": new_id})
        return dict(row)

    def update_trend(self, trend_id, changes, audit):
        self._record("update_trend", trend_id=trend_id, changes=changes, audit=audit)
        if trend_id not in self.trends:
            return None
        slug = changes.get("slug")
        if slug and any(t["slug"] == slug and t["id"] != trend_id for t in self.trends.values()):
            raise _integrity_error("23505")
        self.trends[trend_id].update(changes)
        self.audit.append(audit)
        return dict(self.trends[trend_id])

    def delete_trend(self, trend_id, audit):
        self._record("delete_trend", trend_id=trend_id, audit=audit)
        if self.trend_in_use:
            raise _integrity_error("23503")
        row = self.trends.pop(trend_id, None)
        if row is None:
            return None
        self.audit.append(audit)
        return {"id": row["id"], "slug": row["slug"], "name": row["name"]}

    def list_audit_log(self, *, offset, limit):
        self._record("list_audit_log", offset=offset, limit=limit)
        rows = [
            {
                "id": str(uuid.uuid4()), "admin_email": ADMIN_EMAIL, "action": "user.disable",
                "target_type": "user", "target_id": USER_ID, "details": {"was_disabled": False},
                "created_at": "2026-06-20T10:00:00+00:00",
            }
        ]
        return self._page(rows, offset, limit)

    def called(self, name):
        return [kwargs for call, kwargs in self.calls if call == name]


@pytest.fixture
def repo(monkeypatch):
    fake = FakeAdminRepo()
    monkeypatch.setattr(admin_router, "admin_repo", fake)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", f"{ADMIN_EMAIL}, {OTHER_ADMIN_EMAIL.upper()}")
    return fake


def _client(user_id, email):
    token = create_session_token(user_id, email)
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def api(repo):
    return _client(ADMIN_ID, ADMIN_EMAIL)


@pytest.fixture
def removed(monkeypatch):
    calls = []

    def fake_remove(bucket, paths):
        calls.append((bucket, list(paths)))
        if bucket == settings.PRODUCT_ASSETS_BUCKET:
            raise storage.StorageError("storage is down")
        if bucket == settings.AVATARS_BUCKET:
            raise storage.ObjectNotFoundError("gone")

    monkeypatch.setattr(admin_router.storage, "remove", fake_remove)
    return calls


def _error(response):
    return response.json()["error"]["code"]


# ------------------------------------------------------------------ access

NEW_ENDPOINTS = [
    ("GET", "/admin/overview", None),
    ("GET", "/admin/users", None),
    ("GET", f"/admin/users/{USER_ID}", None),
    ("POST", f"/admin/users/{USER_ID}/verify-email", None),
    ("POST", f"/admin/users/{USER_ID}/disable", None),
    ("POST", f"/admin/users/{USER_ID}/enable", None),
    ("POST", f"/admin/users/{USER_ID}/grant-generations", {"amount": 5}),
    ("POST", f"/admin/users/{USER_ID}/extend-trial", {"days": 7}),
    ("POST", f"/admin/users/{USER_ID}/reset-daily-usage", None),
    ("DELETE", f"/admin/users/{USER_ID}", None),
    ("GET", "/admin/brands", None),
    ("GET", "/admin/generations", None),
    ("GET", "/admin/trends", None),
    ("POST", "/admin/trends", {"name": "New", "slug": "new"}),
    ("PATCH", f"/admin/trends/{TREND_ID}", {"status": "inactive"}),
    ("DELETE", f"/admin/trends/{TREND_ID}", None),
    ("GET", "/admin/audit-log", None),
    ("GET", "/admin/stats", None),
]


@pytest.mark.parametrize(("method", "path", "body"), NEW_ENDPOINTS)
def test_non_admin_gets_403_on_every_admin_endpoint(repo, method, path, body):
    client = _client(USER_ID, USER_EMAIL)

    response = client.request(method, path, json=body)

    assert response.status_code == 403
    assert _error(response) == "FORBIDDEN"
    assert repo.calls == []
    assert repo.audit == []


@pytest.mark.parametrize(("method", "path", "body"), NEW_ENDPOINTS)
def test_anonymous_gets_401_on_every_admin_endpoint(repo, method, path, body):
    response = TestClient(app).request(method, path, json=body)

    assert response.status_code == 401
    assert repo.calls == []


def test_disabled_admin_session_is_rejected(repo, monkeypatch):
    from app.repositories import users

    monkeypatch.setattr(
        users, "account_status", lambda user_id: "disabled" if user_id == ADMIN_ID else "active"
    )

    response = _client(ADMIN_ID, ADMIN_EMAIL).get("/admin/overview")

    assert response.status_code == 403
    assert _error(response) == "ACCOUNT_DISABLED"
    assert repo.calls == []


def test_deleted_admin_session_is_rejected(repo, monkeypatch):
    from app.repositories import users

    monkeypatch.setattr(users, "account_status", lambda user_id: "missing")

    response = _client(ADMIN_ID, ADMIN_EMAIL).get("/admin/overview")

    assert response.status_code == 401
    assert _error(response) == "INVALID_TOKEN"
    assert repo.calls == []


# ------------------------------------------------------------ compatibility


def test_stats_keeps_its_shape(api):
    response = api.get("/admin/stats")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "total_accounts", "total_brands", "total_generations", "generations_by_status",
        "generations_by_provider", "generations_last_7d", "generations_last_30d",
        "brand_kits_complete", "active_provider_keys",
    }
    assert body["generations_by_status"] == {
        "pending": 1, "processing": 0, "succeeded": 3, "failed": 1,
    }


# ------------------------------------------------------------------ overview


def test_overview_happy_path(api, repo):
    response = api.get("/admin/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["users"] == {"total": 3, "verified": 2, "new_7d": 1, "disabled": 1}
    assert body["brands"] == {"total": 2, "kits_complete": 1}
    assert body["generations"]["success_rate_30d"] == pytest.approx(0.75)
    assert body["generations"]["today"] == 1
    assert body["cost"] == {"credits_charged_30d": 3, "estimated_provider_cost_30d": 0.12}

    daily = body["daily"]
    assert len(daily) == 30
    assert daily[0]["date"] == "2026-05-21" and daily[-1]["date"] == "2026-06-19"
    assert [d["date"] for d in daily] == sorted(d["date"] for d in daily)
    assert daily[-1] == {"date": "2026-06-19", "succeeded": 2, "failed": 1}
    assert next(d for d in daily if d["date"] == "2026-06-10")["succeeded"] == 1
    assert sum(d["succeeded"] + d["failed"] for d in daily) == 4  # zero-filled elsewhere

    attention = body["attention"]
    assert attention["needs_review"][0]["needs_review"] is True
    assert attention["recent_failures"][0]["status"] == "failed"
    assert repo.called("list_needs_review") == [{"limit": 20}]
    assert repo.called("list_recent_failures") == [{"limit": 10}]


def test_overview_success_rate_is_null_without_finished_generations(api, repo):
    repo.overview_counts.update(generations_succeeded_30d=0, generations_failed_30d=0,
                                estimated_provider_cost_30d=None)
    repo.daily = []

    body = api.get("/admin/overview").json()

    assert body["generations"]["success_rate_30d"] is None
    assert body["cost"]["estimated_provider_cost_30d"] is None
    assert len(body["daily"]) == 30
    assert date.fromisoformat(body["daily"][-1]["date"]) >= date(2026, 1, 1)


def test_generation_row_shape(api):
    body = api.get("/admin/generations").json()

    first = body["items"][0]
    assert set(first) == {
        "id", "status", "provider", "model", "platform_preset", "error_code",
        "error_message", "created_at", "completed_at", "image_url", "needs_review",
        "brand", "user",
    }
    assert first["image_url"] is None
    assert first["brand"] == {"id": BRAND_ID, "name": "Acme"}
    assert first["user"] == {"id": USER_ID, "email": USER_EMAIL}
    assert body["items"][1]["image_url"] == storage.public_url(
        settings.STORAGE_BUCKET, f"brands/{BRAND_ID}/generations/{GEN_ID}.png"
    )


# ------------------------------------------------------------------ users


def test_list_users_happy_path_and_filters(api, repo):
    response = api.get(
        "/admin/users",
        params={"page": 2, "per_page": 1, "q": "  Person ", "verified": "false", "status": "active"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["per_page"], body["total"]) == (2, 1, 3)
    assert len(body["items"]) == 1
    assert repo.called("list_users") == [
        {"offset": 1, "limit": 1, "q": "Person", "verified": False, "status": "active"}
    ]


def test_list_users_defaults(api, repo):
    body = api.get("/admin/users").json()

    assert body["per_page"] == 24 and body["page"] == 1
    assert repo.called("list_users")[0] == {
        "offset": 0, "limit": 24, "q": None, "verified": None, "status": None,
    }
    user = next(u for u in body["items"] if u["id"] == USER_ID)
    assert user == {
        "id": USER_ID,
        "email": USER_EMAIL,
        "full_name": "Test Person",
        "email_verified": False,
        "disabled": False,
        "is_admin": False,
        "created_at": "2026-06-01T09:00:00Z",
        "trial_ends_at": "2026-06-15T09:00:00Z",
        "brands_count": 2,
        "generations_count": 5,
        "generations_succeeded": 3,
        "quota": {"limit": 42, "consumed": 3, "reserved": 1, "remaining": 38},
        "credits": {"balance": 39, "reserved": 1, "available": 38},
        "today": {"limit": 3, "consumed": 2, "reserved": 1},
    }
    admin = next(u for u in body["items"] if u["id"] == OTHER_ADMIN_ID)
    assert admin["is_admin"] is True


def test_user_without_quota_rows_has_null_blocks(api, repo):
    repo.users[USER_ID].update(
        quota_limit=None, quota_consumed=None, quota_reserved=None,
        credits_balance=None, credits_reserved=None,
        today_limit=None, today_consumed=None, today_reserved=None,
    )

    body = api.get(f"/admin/users/{USER_ID}").json()

    assert (body["quota"], body["credits"], body["today"]) == (None, None, None)


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -3},
        {"per_page": 0},
        {"per_page": 101},
        {"per_page": "lots"},
        {"verified": "maybe"},
        {"status": "banned"},
    ],
)
def test_list_users_validation_errors(api, repo, params):
    response = api.get("/admin/users", params=params)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("list_users") == []


def test_get_user_detail(api, repo):
    repo.ledger[USER_ID] = [{
        "id": str(uuid.uuid4()), "operation": "reserve", "amount": 1,
        "metadata": {"amount": 1}, "created_at": "2026-06-19T12:00:00+00:00",
    }]

    response = api.get(f"/admin/users/{USER_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == USER_EMAIL and body["quota"]["remaining"] == 38
    assert body["brands"] == [{
        "id": BRAND_ID, "name": "Acme", "kit_status": "complete",
        "generation_count": 5, "created_at": "2026-06-02T09:00:00Z",
    }]
    assert body["recent_generations"][0]["id"] == GEN_ID
    assert body["credit_ledger"][0]["operation"] == "reserve"
    assert repo.called("list_user_generations") == [{"user_id": USER_ID, "limit": 10}]
    assert repo.called("list_user_ledger") == [{"user_id": USER_ID, "limit": 20}]


@pytest.mark.parametrize("user_id", [UNKNOWN_ID, "not-a-uuid"])
def test_get_unknown_user_is_404(api, user_id):
    response = api.get(f"/admin/users/{user_id}")

    assert response.status_code == 404
    assert _error(response) == "USER_NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("verify-email", None),
        ("disable", None),
        ("enable", None),
        ("grant-generations", {"amount": 1}),
        ("extend-trial", {"days": 1}),
        ("reset-daily-usage", None),
    ],
)
@pytest.mark.parametrize("user_id", [UNKNOWN_ID, "nope"])
def test_actions_on_unknown_user_are_404(api, repo, path, body, user_id):
    response = api.post(f"/admin/users/{user_id}/{path}", json=body)

    assert response.status_code == 404
    assert _error(response) == "USER_NOT_FOUND"
    assert repo.audit == []


@pytest.mark.parametrize("user_id", [UNKNOWN_ID, "nope"])
def test_delete_unknown_user_is_404(api, repo, user_id):
    response = api.delete(f"/admin/users/{user_id}")

    assert response.status_code == 404
    assert _error(response) == "USER_NOT_FOUND"
    assert repo.audit == []


def test_verify_email_action(api, repo):
    response = api.post(f"/admin/users/{USER_ID}/verify-email")

    assert response.status_code == 200
    assert response.json()["email_verified"] is True
    assert repo.audit == [{
        "admin_user_id": ADMIN_ID, "admin_email": ADMIN_EMAIL, "action": "user.verify_email",
        "target_type": "user", "target_id": USER_ID, "details": {},
    }]


def test_disable_then_enable_actions(api, repo):
    disabled = api.post(f"/admin/users/{USER_ID}/disable")
    assert disabled.status_code == 200
    assert disabled.json()["disabled"] is True

    enabled = api.post(f"/admin/users/{USER_ID}/enable")
    assert enabled.status_code == 200
    assert enabled.json()["disabled"] is False

    assert [a["action"] for a in repo.audit] == ["user.disable", "user.enable"]
    assert all(a["target_type"] == "user" and a["target_id"] == USER_ID for a in repo.audit)
    assert [c["disabled"] for c in repo.called("set_user_disabled")] == [True, False]


@pytest.mark.parametrize("action", ["disable", "enable", "delete"])
@pytest.mark.parametrize(
    "target",
    [pytest.param(ADMIN_ID, id="self"), pytest.param(OTHER_ADMIN_ID, id="other-admin")],
)
def test_admin_targets_are_forbidden(api, repo, removed, action, target):
    if action == "delete":
        response = api.delete(f"/admin/users/{target}")
    else:
        response = api.post(f"/admin/users/{target}/{action}")

    assert response.status_code == 403
    assert _error(response) == "ADMIN_TARGET_FORBIDDEN"
    assert repo.audit == []
    assert repo.called("set_user_disabled") == [] and repo.called("delete_user") == []
    assert target in repo.users
    assert removed == []


def test_admin_email_target_is_forbidden_case_insensitively(api, repo):
    repo.users[USER_ID]["email"] = OTHER_ADMIN_EMAIL.title()

    response = api.post(f"/admin/users/{USER_ID}/disable")

    assert response.status_code == 403
    assert _error(response) == "ADMIN_TARGET_FORBIDDEN"


def test_grant_generations_raises_quota_and_credits_with_a_ledger_row(api, repo):
    credits = 5 * max(settings.GENERATION_CREDIT_COST, 1)  # 5 with the default cost of 1

    response = api.post(
        f"/admin/users/{USER_ID}/grant-generations", json={"amount": 5, "note": "  launch promo "}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["quota"] == {"limit": 47, "consumed": 3, "reserved": 1, "remaining": 43}
    assert body["credits"] == {
        "balance": 39 + credits, "reserved": 1, "available": 38 + credits,
    }

    (call,) = repo.called("grant_generations")
    assert call["generations"] == 5
    assert call["credits"] == credits
    assert call["idempotency_key"].startswith("admin-grant:")
    assert call["metadata"]["note"] == "launch promo"
    assert call["metadata"]["admin_email"] == ADMIN_EMAIL

    (audit,) = repo.audit
    assert audit["action"] == "user.grant_generations"
    assert audit["details"]["amount"] == 5 and audit["details"]["note"] == "launch promo"
    assert audit["details"]["ledger_idempotency_key"] == call["idempotency_key"]

    ledger = api.get(f"/admin/users/{USER_ID}").json()["credit_ledger"]
    assert ledger[0]["operation"] == "grant" and ledger[0]["amount"] == call["credits"]


def test_each_grant_uses_a_unique_ledger_key(api, repo):
    api.post(f"/admin/users/{USER_ID}/grant-generations", json={"amount": 1})
    api.post(f"/admin/users/{USER_ID}/grant-generations", json={"amount": 1})

    keys = [c["idempotency_key"] for c in repo.called("grant_generations")]
    assert len(set(keys)) == 2


@pytest.mark.parametrize(
    "body",
    [
        {"amount": 0},
        {"amount": 1001},
        {"amount": -5},
        {"amount": "5"},
        {"amount": 2.5},
        {"amount": True},
        {"amount": 5, "note": "x" * 301},
        {},
        None,
    ],
)
def test_grant_generations_validation(api, repo, body):
    response = api.post(f"/admin/users/{USER_ID}/grant-generations", json=body)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("grant_generations") == []


def test_extend_trial_action(api, repo):
    response = api.post(f"/admin/users/{USER_ID}/extend-trial", json={"days": 30})

    assert response.status_code == 200
    assert response.json()["trial_ends_at"] == "2026-07-15T09:00:00Z"
    assert repo.called("extend_trial")[0]["days"] == 30
    assert repo.audit[0]["action"] == "user.extend_trial"
    assert repo.audit[0]["details"] == {"days": 30}


@pytest.mark.parametrize("body", [{"days": 0}, {"days": 366}, {"days": "7"}, {}])
def test_extend_trial_validation(api, repo, body):
    response = api.post(f"/admin/users/{USER_ID}/extend-trial", json=body)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("extend_trial") == []


def test_reset_daily_usage_action(api, repo):
    response = api.post(f"/admin/users/{USER_ID}/reset-daily-usage")

    assert response.status_code == 200
    assert response.json()["today"] == {"limit": 3, "consumed": 0, "reserved": 1}
    assert repo.audit[0]["action"] == "user.reset_daily_usage"


def test_delete_user_removes_storage_best_effort(api, repo, removed):
    response = api.delete(f"/admin/users/{USER_ID}")

    assert response.status_code == 204
    assert response.content == b""
    assert USER_ID not in repo.users
    assert repo.audit[0]["action"] == "user.delete"
    assert repo.audit[0]["target_id"] == USER_ID
    buckets = {bucket: paths for bucket, paths in removed}
    assert sorted(buckets[settings.STORAGE_BUCKET]) == sorted(repo.delete_files["brand_files"])
    assert buckets[settings.PRODUCT_ASSETS_BUCKET] == repo.delete_files["product_asset_files"]
    assert buckets[settings.AVATARS_BUCKET] == repo.delete_files["avatar_files"]


# ------------------------------------------------------------------ brands


def test_list_brands_new_shape(api, repo):
    response = api.get("/admin/brands", params={"q": "acme", "kit_status": "complete"})

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item == {
        "id": BRAND_ID,
        "name": "Acme",
        "owner": {"id": USER_ID, "email": USER_EMAIL, "full_name": "Test Person"},
        "kit_status": "complete",
        "colors_count": 4,
        "has_logo": True,
        "generation_count": 5,
        "created_at": "2026-06-02T09:00:00Z",
    }
    assert repo.called("list_brands") == [
        {"offset": 0, "limit": 24, "q": "acme", "kit_status": "complete"}
    ]


def test_list_brands_keeps_old_pagination_params(api, repo):
    response = api.get("/admin/brands", params={"page": 3, "per_page": 10})

    assert response.status_code == 200
    assert (response.json()["page"], response.json()["per_page"]) == (3, 10)
    assert repo.called("list_brands")[0]["offset"] == 20


@pytest.mark.parametrize("params", [{"page": 0}, {"per_page": 101}, {"kit_status": "done"}])
def test_list_brands_validation(api, params):
    response = api.get("/admin/brands", params=params)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"


# ------------------------------------------------------------------ generations


def test_list_generations_filters(api, repo):
    response = api.get(
        "/admin/generations",
        params={
            "page": 1, "per_page": 50, "status": "failed", "provider": "openai",
            "needs_review": "true", "q": "acme", "from": "2026-06-01", "to": "2026-06-30",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert repo.called("list_generations") == [{
        "offset": 0, "limit": 50, "status": "failed", "provider": "openai",
        "needs_review": True, "q": "acme",
        "date_from": date(2026, 6, 1), "date_to": date(2026, 6, 30),
    }]


@pytest.mark.parametrize(
    "params",
    [
        {"status": "done"},
        {"provider": "midjourney"},
        {"needs_review": "perhaps"},
        {"from": "2026-13-01"},
        {"to": "yesterday"},
        {"from": "2026-06-30", "to": "2026-06-01"},
        {"per_page": 1000},
    ],
)
def test_list_generations_validation(api, repo, params):
    response = api.get("/admin/generations", params=params)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("list_generations") == []


# ------------------------------------------------------------------ trends


def test_list_trends_returns_string_arrays(api, repo):
    response = api.get("/admin/trends", params={"q": "pastel", "status": "active"})

    assert response.status_code == 200
    trend = response.json()["items"][0]
    assert trend["keywords"] == ["calm", "7"]
    assert set(trend) == {
        "id", "name", "slug", "description", "category", "industry", "region", "platform",
        "audience", "visual_style", "content_patterns", "keywords", "avoid_patterns",
        "popularity_score", "growth_score", "relevance_score", "status", "source",
        "observed_at", "expires_at", "created_at", "updated_at",
    }
    assert repo.called("list_trends") == [
        {"offset": 0, "limit": 24, "q": "pastel", "status": "active"}
    ]


def test_list_trends_rejects_unknown_status(api):
    response = api.get("/admin/trends", params={"status": "draft"})

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"


def test_create_trend(api, repo):
    response = api.post(
        "/admin/trends",
        json={
            "name": "  Bold Neon  ", "slug": "bold-neon", "keywords": ["neon"],
            "popularity_score": 100, "growth_score": 0, "status": "inactive",
            "expires_at": "2026-12-31T00:00:00Z",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["slug"], body["status"]) == ("Bold Neon", "bold-neon", "inactive")
    assert body["keywords"] == ["neon"] and body["popularity_score"] == 100
    (audit,) = repo.audit
    assert (audit["action"], audit["target_type"]) == ("trend.create", "trend")
    values = repo.called("create_trend")[0]["values"]
    assert values["region"] == [] and values["relevance_score"] == 0


def test_create_trend_derives_slug_from_name(api, repo):
    response = api.post("/admin/trends", json={"name": "Summer Glow 2026!"})

    assert response.status_code == 201
    assert response.json()["slug"] == "summer-glow-2026"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "   "},
        {"name": "مرحبا"},  # no ASCII to derive a slug from, and none given
        {"name": "X", "slug": "Has Caps"},
        {"name": "X", "slug": "under_score"},
        {"name": "X", "slug": ""},
        {"name": "X", "slug": "ok", "popularity_score": 101},
        {"name": "X", "slug": "ok", "growth_score": -1},
        {"name": "X", "slug": "ok", "relevance_score": "50"},
        {"name": "X", "slug": "ok", "status": "draft"},
        {"name": "X", "slug": "ok", "keywords": "not-a-list"},
    ],
)
def test_create_trend_validation(api, repo, body):
    response = api.post("/admin/trends", json=body)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("create_trend") == []


def test_create_trend_duplicate_slug_is_409(api, repo):
    response = api.post("/admin/trends", json={"name": "Again", "slug": "soft-pastels"})

    assert response.status_code == 409
    assert _error(response) == "TREND_SLUG_TAKEN"


def test_patch_trend_sends_only_given_fields(api, repo):
    response = api.patch(
        f"/admin/trends/{TREND_ID}", json={"status": "inactive", "description": None}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    (call,) = repo.called("update_trend")
    assert call["changes"] == {"status": "inactive", "description": None}
    assert repo.audit[0]["action"] == "trend.update"
    assert repo.audit[0]["target_id"] == TREND_ID


@pytest.mark.parametrize(
    "body",
    [
        {"name": None},
        {"name": " "},
        {"slug": "Bad!"},
        {"status": None},
        {"popularity_score": None},
        {"keywords": None},
        {"growth_score": 1000},
    ],
)
def test_patch_trend_validation(api, repo, body):
    response = api.patch(f"/admin/trends/{TREND_ID}", json=body)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
    assert repo.called("update_trend") == []


def test_patch_trend_duplicate_slug_is_409(api, repo):
    repo.trends[UNKNOWN_ID] = trend_row(id=UNKNOWN_ID, slug="taken")

    response = api.patch(f"/admin/trends/{TREND_ID}", json={"slug": "taken"})

    assert response.status_code == 409
    assert _error(response) == "TREND_SLUG_TAKEN"


@pytest.mark.parametrize("trend_id", [UNKNOWN_ID, "nope"])
def test_unknown_trend_is_404(api, trend_id):
    patch = api.patch(f"/admin/trends/{trend_id}", json={"status": "inactive"})
    delete = api.delete(f"/admin/trends/{trend_id}")

    assert (patch.status_code, _error(patch)) == (404, "TREND_NOT_FOUND")
    assert (delete.status_code, _error(delete)) == (404, "TREND_NOT_FOUND")


def test_delete_trend(api, repo):
    response = api.delete(f"/admin/trends/{TREND_ID}")

    assert response.status_code == 204
    assert TREND_ID not in repo.trends
    assert repo.audit[0]["action"] == "trend.delete"


def test_delete_trend_blocked_by_a_reference_is_409(api, repo):
    repo.trend_in_use = True

    response = api.delete(f"/admin/trends/{TREND_ID}")

    assert response.status_code == 409
    assert _error(response) == "TREND_IN_USE"
    assert TREND_ID in repo.trends


# ------------------------------------------------------------------ audit log


def test_audit_log_page(api, repo):
    response = api.get("/admin/audit-log", params={"page": 1, "per_page": 5})

    assert response.status_code == 200
    body = response.json()
    assert (body["page"], body["per_page"], body["total"]) == (1, 5, 1)
    assert set(body["items"][0]) == {
        "id", "admin_email", "action", "target_type", "target_id", "details", "created_at",
    }


@pytest.mark.parametrize("params", [{"page": 0}, {"per_page": 0}, {"per_page": 101}])
def test_audit_log_validation(api, params):
    response = api.get("/admin/audit-log", params=params)

    assert response.status_code == 400
    assert _error(response) == "VALIDATION_ERROR"
