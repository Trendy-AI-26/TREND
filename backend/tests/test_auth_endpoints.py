"""Auth endpoints end to end, with an in-memory stand-in for the users repository."""

import itertools
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.core.security import SESSION_COOKIE_NAME
from app.main import app
from app.routers import auth as auth_router
from app.services import auth_service


class FakeUsersRepo:
    """Mirrors app.repositories.users on plain dicts."""

    def __init__(self):
        self.users: dict[str, dict] = {}
        self.codes: list[dict] = []
        self._seq = itertools.count()

    def get_user_by_email(self, email):
        return next(
            (u for u in self.users.values() if u["email"].lower() == email.lower()), None
        )

    def get_user_by_id(self, user_id):
        return self.users.get(str(user_id))

    def create_user(self, email, password_hash, full_name):
        user_id = uuid.uuid4()
        if self.get_user_by_email(email):
            raise db.IntegrityError("insert", {}, Exception("duplicate"))
        user = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "email_verified_at": None,
            "created_at": datetime.now(timezone.utc),
            "full_name": full_name,
        }
        self.users[str(user_id)] = user
        return user

    def update_unverified_user(self, user_id, password_hash, full_name):
        user = self.users[str(user_id)]
        user["password_hash"] = password_hash
        if full_name is not None:
            user["full_name"] = full_name

    def mark_email_verified(self, user_id, when):
        user = self.users[str(user_id)]
        user["email_verified_at"] = user["email_verified_at"] or when

    def set_password(self, user_id, password_hash, verified_at):
        user = self.users[str(user_id)]
        user["password_hash"] = password_hash
        user["email_verified_at"] = user["email_verified_at"] or verified_at

    def latest_code(self, user_id, purpose):
        rows = [
            c for c in self.codes if c["user_id"] == str(user_id) and c["purpose"] == purpose
        ]
        return max(rows, key=lambda c: c["seq"], default=None)

    def replace_code(self, user_id, purpose, code_hash, expires_at, now):
        for c in self.codes:
            if (
                c["user_id"] == str(user_id)
                and c["purpose"] == purpose
                and c["consumed_at"] is None
            ):
                c["consumed_at"] = now
        self.codes.append(
            {
                "id": uuid.uuid4(),
                "seq": next(self._seq),
                "user_id": str(user_id),
                "purpose": purpose,
                "code_hash": code_hash,
                "expires_at": expires_at,
                "attempts": 0,
                "consumed_at": None,
                "created_at": now,
            }
        )

    def increment_attempts(self, code_id):
        for c in self.codes:
            if c["id"] == code_id and c["consumed_at"] is None:
                c["attempts"] += 1
                return c["attempts"]
        return None

    def consume_code(self, code_id, now):
        for c in self.codes:
            if c["id"] == code_id and c["consumed_at"] is None:
                c["consumed_at"] = now
                return True
        return False


class Clock:
    def __init__(self):
        self.now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)

    def __call__(self):
        return self.now


@pytest.fixture
def repo(monkeypatch):
    fake = FakeUsersRepo()
    monkeypatch.setattr(auth_service, "users_repo", fake)
    return fake


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(auth_service, "_now", c)
    return c


@pytest.fixture
def outbox(monkeypatch):
    sent = []

    async def fake_send(to, code, purpose):
        sent.append({"to": to, "code": code, "purpose": purpose})

    monkeypatch.setattr(auth_router, "send_code_email", fake_send)
    return sent


@pytest.fixture
def api(repo, clock, outbox):
    return TestClient(app)


EMAIL = "Person@Example.com"
PASSWORD = "correct horse battery"


def _signup(api, email=EMAIL, password=PASSWORD, **extra):
    return api.post("/auth/signup", json={"email": email, "password": password, **extra})


def _verified_user(api, outbox, email=EMAIL, password=PASSWORD):
    assert _signup(api, email, password, full_name="Test Person").status_code == 201
    response = api.post("/auth/verify-email", json={"email": email, "code": outbox[-1]["code"]})
    assert response.status_code == 200
    return response


# ------------------------------------------------------------------ signup


def test_signup_creates_unverified_user_and_sends_code(api, repo, outbox):
    response = _signup(api, full_name="  Test Person ")

    assert response.status_code == 201
    assert response.json() == {"email": "person@example.com", "verification_required": True}
    user = repo.get_user_by_email("person@example.com")
    assert user["email_verified_at"] is None
    assert user["full_name"] == "Test Person"
    assert user["password_hash"].startswith("$2")  # bcrypt, never the plain password
    assert len(outbox) == 1
    assert re.fullmatch(r"\d{6}", outbox[0]["code"])
    assert outbox[0]["purpose"] == "verify_email"
    assert outbox[0]["to"] == "person@example.com"
    # Only a hash of the code is stored.
    assert outbox[0]["code"] not in repo.codes[0]["code_hash"]
    assert SESSION_COOKIE_NAME not in response.cookies


def test_signup_rejects_existing_verified_email(api, outbox):
    _verified_user(api, outbox)

    response = _signup(api, "person@example.com")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert "request_id" in response.json()["error"]


def test_signup_for_unverified_email_resends_code_after_cooldown(api, repo, outbox, clock):
    _signup(api, password="first password")
    clock.advance(61)

    response = _signup(api, password="second password")

    assert response.status_code == 201
    assert response.json()["verification_required"] is True
    assert len(outbox) == 2
    assert len(repo.users) == 1
    # The latest sign-up wins, and the first code stops working.
    assert auth_service.security.verify_password(
        "second password", repo.get_user_by_email("person@example.com")["password_hash"]
    )
    old = api.post(
        "/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]}
    )
    assert old.status_code == 400


def test_signup_for_unverified_email_within_cooldown_still_returns_201(api, outbox):
    _signup(api)

    response = _signup(api)

    assert response.status_code == 201
    assert len(outbox) == 1


@pytest.mark.parametrize("password", ["short", "x" * 73])
def test_signup_validates_password(api, password):
    response = _signup(api, password=password)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_signup_validates_email_and_full_name(api):
    assert _signup(api, email="not-an-email").status_code == 400
    response = _signup(api, full_name="x")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------ verify-email


def test_verify_email_sets_session_cookie_and_returns_user(api, repo, outbox):
    _signup(api, full_name="Test Person")

    response = api.post("/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]})

    assert response.status_code == 200
    user = response.json()["user"]
    assert set(user) == {"id", "email", "full_name", "is_admin", "email_verified"}
    assert user["email"] == "person@example.com"
    assert user["full_name"] == "Test Person"
    assert user["email_verified"] is True
    assert user["is_admin"] is False
    assert repo.get_user_by_email(EMAIL)["email_verified_at"] is not None

    set_cookie = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "httponly" in set_cookie
    assert "path=/" in set_cookie
    assert "samesite=lax" in set_cookie
    assert f"max-age={settings.AUTH_SESSION_TTL_SECONDS}" in set_cookie
    assert "secure" not in set_cookie


def test_session_cookie_is_secure_when_configured(api, outbox, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)
    response = _verified_user(api, outbox)

    assert "secure" in response.headers["set-cookie"].lower()


def test_code_cannot_be_reused(api, outbox):
    _verified_user(api, outbox)

    again = api.post("/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]})

    assert again.status_code == 400
    assert again.json()["error"]["code"] == "INVALID_CODE"


def test_verify_email_wrong_code(api, outbox):
    _signup(api)
    wrong = "000000" if outbox[0]["code"] != "000000" else "111111"

    response = api.post("/auth/verify-email", json={"email": EMAIL, "code": wrong})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CODE"


def test_verify_email_unknown_account_looks_like_wrong_code(api):
    response = api.post("/auth/verify-email", json={"email": "ghost@example.com", "code": "123456"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CODE"


def test_verify_email_expired_code(api, outbox, clock):
    _signup(api)
    clock.advance(15 * 60 + 1)

    response = api.post("/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CODE_EXPIRED"


def test_code_is_still_valid_just_before_expiry(api, outbox, clock):
    _signup(api)
    clock.advance(15 * 60 - 1)

    response = api.post("/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]})

    assert response.status_code == 200


def test_too_many_wrong_attempts_lock_the_code(api, outbox):
    _signup(api)
    real = outbox[0]["code"]
    wrong = "000000" if real != "000000" else "111111"

    for _ in range(5):
        response = api.post("/auth/verify-email", json={"email": EMAIL, "code": wrong})
        assert response.json()["error"]["code"] == "INVALID_CODE"

    # Even the right code is refused now.
    response = api.post("/auth/verify-email", json={"email": EMAIL, "code": real})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


def test_four_wrong_attempts_then_right_code_still_works(api, outbox):
    _signup(api)
    real = outbox[0]["code"]
    wrong = "000000" if real != "000000" else "111111"

    for _ in range(4):
        api.post("/auth/verify-email", json={"email": EMAIL, "code": wrong})

    assert api.post("/auth/verify-email", json={"email": EMAIL, "code": real}).status_code == 200


# ------------------------------------------------------------ resend-code


def test_resend_code_for_unknown_email_is_a_silent_success(api, outbox):
    response = api.post(
        "/auth/resend-code", json={"email": "ghost@example.com", "purpose": "verify_email"}
    )

    assert response.status_code == 200
    assert response.json() == {"sent": True}
    assert outbox == []


def test_resend_code_enforces_cooldown_silently(api, outbox, clock):
    _signup(api)

    first = api.post("/auth/resend-code", json={"email": EMAIL, "purpose": "verify_email"})
    assert first.json() == {"sent": True}
    assert len(outbox) == 1  # sign-up's code is still inside the 60 s cooldown

    clock.advance(60)
    second = api.post("/auth/resend-code", json={"email": EMAIL, "purpose": "verify_email"})
    assert second.json() == {"sent": True}
    assert len(outbox) == 2
    assert outbox[1]["code"] != "" and outbox[1]["purpose"] == "verify_email"


def test_resend_code_rejects_unknown_purpose(api):
    response = api.post("/auth/resend-code", json={"email": EMAIL, "purpose": "nope"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_resend_reset_code_only_for_verified_accounts(api, outbox, clock):
    _signup(api)
    outbox.clear()
    clock.advance(61)

    response = api.post("/auth/resend-code", json={"email": EMAIL, "purpose": "reset_password"})

    assert response.json() == {"sent": True}
    assert outbox == []


# -------------------------------------------------------------------- login


def test_login_success_sets_cookie(api, outbox):
    _verified_user(api, outbox)
    api.cookies.clear()

    response = api.post("/auth/login", json={"email": "PERSON@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert SESSION_COOKIE_NAME in response.cookies


def test_login_wrong_password(api, outbox):
    _verified_user(api, outbox)

    response = api.post("/auth/login", json={"email": EMAIL, "password": "wrong password"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert SESSION_COOKIE_NAME not in response.cookies


def test_login_unknown_email_is_indistinguishable(api):
    response = api.post("/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unverified_account_gets_403_and_a_fresh_code(api, outbox, clock):
    _signup(api)
    clock.advance(61)

    response = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert len(outbox) == 2
    assert outbox[1]["purpose"] == "verify_email"


def test_login_unverified_with_wrong_password_does_not_leak_status(api, outbox):
    _signup(api)

    response = api.post("/auth/login", json={"email": EMAIL, "password": "wrong password"})

    assert response.status_code == 401
    assert len(outbox) == 1


# ---------------------------------------------------- session and logout


def test_session_requires_authentication(api):
    response = api.get("/auth/session")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_session_returns_user_from_cookie(api, outbox):
    _verified_user(api, outbox)  # the client keeps the cookie

    response = api.get("/auth/session")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert response.json()["user"]["email_verified"] is True


def test_session_accepts_bearer_token_and_reports_admin(api, outbox, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "person@example.com")
    verified = _verified_user(api, outbox)
    token = verified.cookies[SESSION_COOKIE_NAME]
    api.cookies.clear()

    response = api.get("/auth/session", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True


def test_session_for_deleted_user_is_401(api, repo, outbox):
    _verified_user(api, outbox)
    repo.users.clear()

    assert api.get("/auth/session").status_code == 401


def test_logout_clears_the_cookie(api, outbox):
    _verified_user(api, outbox)

    response = api.post("/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    set_cookie = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "max-age=0" in set_cookie
    assert api.get("/auth/session").status_code == 401


# ---------------------------------------------------------- password reset


def _start_reset(api, outbox):
    outbox.clear()
    response = api.post("/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 200
    return outbox[-1]["code"]


def test_forgot_password_never_reveals_whether_the_account_exists(api, outbox):
    response = api.post("/auth/forgot-password", json={"email": "ghost@example.com"})

    assert response.status_code == 200
    assert response.json() == {"sent": True}
    assert outbox == []


def test_full_password_reset_flow(api, outbox, clock):
    _verified_user(api, outbox)
    api.cookies.clear()
    clock.advance(61)
    code = _start_reset(api, outbox)
    assert outbox[-1]["purpose"] == "reset_password"

    verified = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": code})
    assert verified.status_code == 200
    reset_token = verified.json()["reset_token"]

    done = api.post(
        "/auth/reset-password", json={"reset_token": reset_token, "password": "brand new secret"}
    )
    assert done.status_code == 200
    assert done.json() == {"ok": True}

    old = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert old.status_code == 401
    new = api.post("/auth/login", json={"email": EMAIL, "password": "brand new secret"})
    assert new.status_code == 200

    # The same token cannot be replayed once the password changed.
    replay = api.post(
        "/auth/reset-password", json={"reset_token": reset_token, "password": "yet another one"}
    )
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_verify_reset_code_errors(api, outbox, clock):
    _verified_user(api, outbox)
    clock.advance(61)
    code = _start_reset(api, outbox)
    wrong = "000000" if code != "000000" else "111111"

    bad = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": wrong})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "INVALID_CODE"

    ghost = api.post("/auth/verify-reset-code", json={"email": "ghost@example.com", "code": code})
    assert ghost.json()["error"]["code"] == "INVALID_CODE"

    clock.advance(15 * 60 + 1)
    expired = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": code})
    assert expired.json()["error"]["code"] == "CODE_EXPIRED"


def test_verify_code_purposes_do_not_mix(api, outbox, clock):
    _signup(api)
    verify_code = outbox[0]["code"]

    response = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": verify_code})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CODE"


def test_reset_password_rejects_garbage_and_session_tokens(api, outbox):
    verified = _verified_user(api, outbox)
    session_token = verified.cookies[SESSION_COOKIE_NAME]

    for token in ("garbage", session_token):
        response = api.post(
            "/auth/reset-password", json={"reset_token": token, "password": "brand new secret"}
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_reset_password_enforces_minimum_length(api, outbox, clock):
    _verified_user(api, outbox)
    clock.advance(61)
    code = _start_reset(api, outbox)
    token = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": code}).json()[
        "reset_token"
    ]

    response = api.post("/auth/reset-password", json={"reset_token": token, "password": "short"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reset_token_expires_after_15_minutes(api, outbox, clock, monkeypatch):
    # JWT expiry uses the real clock, so check the claim instead of waiting.
    import jwt

    _verified_user(api, outbox)
    clock.advance(61)
    code = _start_reset(api, outbox)
    token = api.post("/auth/verify-reset-code", json={"email": EMAIL, "code": code}).json()[
        "reset_token"
    ]
    claims = jwt.decode(token, settings.AUTH_JWT_SECRET, algorithms=["HS256"], audience="trendy")

    assert claims["purpose"] == "reset"
    assert claims["exp"] - claims["iat"] == 15 * 60
    assert claims["iss"] == "trendy-api"
