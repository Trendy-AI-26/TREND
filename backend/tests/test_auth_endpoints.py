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

    def issue_code_if_allowed(
        self, user_id, purpose, code_hash, expires_at, now, cooldown_seconds
    ):
        user = self.users.get(str(user_id))
        if user is None:
            return "missing"
        verified = user["email_verified_at"] is not None
        if purpose == "verify_email" and verified:
            return "ineligible"
        if purpose == "reset_password" and not verified:
            return "ineligible"

        latest = self.latest_code(user_id, purpose)
        if latest is not None:
            age = (now - latest["created_at"]).total_seconds()
            if age < cooldown_seconds:
                return "cooldown"

        self.replace_code(user_id, purpose, code_hash, expires_at, now)
        return "issued"

    def consume_verification_code_and_mark_verified(self, user_id, code_id, now):
        user = self.users.get(str(user_id))
        if user is None or user["email_verified_at"] is not None:
            return False
        for code in self.codes:
            if (
                code["id"] == code_id
                and code["user_id"] == str(user_id)
                and code["purpose"] == "verify_email"
                and code["consumed_at"] is None
            ):
                code["consumed_at"] = now
                user["email_verified_at"] = now
                return True
        return False

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
    _signup(api, password="first password", full_name="Original Name")
    clock.advance(61)

    response = _signup(api, password="second password", full_name="Attacker Name")

    assert response.status_code == 201
    assert response.json()["verification_required"] is True
    assert len(outbox) == 2
    assert len(repo.users) == 1
    # A repeated sign-up is only a resend request. It must never replace
    # credentials or profile data for an account the caller does not control.
    assert auth_service.security.verify_password(
        "first password", repo.get_user_by_email("person@example.com")["password_hash"]
    )
    assert not auth_service.security.verify_password(
        "second password", repo.get_user_by_email("person@example.com")["password_hash"]
    )
    assert repo.get_user_by_email("person@example.com")["full_name"] == "Original Name"

    # Once the cooldown has elapsed, the newly emailed code replaces the old
    # one, but the account credentials remain unchanged.
    old = api.post(
        "/auth/verify-email", json={"email": EMAIL, "code": outbox[0]["code"]}
    )
    assert old.status_code == 400
    current = api.post(
        "/auth/verify-email", json={"email": EMAIL, "code": outbox[1]["code"]}
    )
    assert current.status_code == 200


def test_signup_for_unverified_email_within_cooldown_keeps_credentials_and_code(
    api, repo, outbox
):
    _signup(api, password="first password", full_name="Original Name")
    first_code = outbox[0]["code"]

    response = _signup(api, password="second password", full_name="Attacker Name")

    assert response.status_code == 201
    assert len(outbox) == 1
    user = repo.get_user_by_email("person@example.com")
    assert auth_service.security.verify_password("first password", user["password_hash"])
    assert not auth_service.security.verify_password("second password", user["password_hash"])
    assert user["full_name"] == "Original Name"

    # No replacement email is sent during cooldown, so the existing code must
    # remain usable by the mailbox owner.
    verified = api.post(
        "/auth/verify-email", json={"email": EMAIL, "code": first_code}
    )
    assert verified.status_code == 200


def test_concurrent_first_signup_loser_keeps_winning_credentials(
    api, repo, outbox, monkeypatch
):
    winner = repo.create_user(
        "person@example.com",
        auth_service.security.hash_password("winner password"),
        "Winner Name",
    )
    calls = 0

    def initially_missing(email):
        nonlocal calls
        calls += 1
        return None if calls == 1 else winner

    def duplicate_create(email, password_hash, full_name):
        raise db.IntegrityError("insert", {}, Exception("duplicate email"))

    monkeypatch.setattr(repo, "get_user_by_email", initially_missing)
    monkeypatch.setattr(repo, "create_user", duplicate_create)
    monkeypatch.setattr(db, "is_unique_violation", lambda exc, constraint: True)

    response = _signup(api, password="loser password", full_name="Loser Name")

    assert response.status_code == 201
    assert auth_service.security.verify_password(
        "winner password", winner["password_hash"]
    )
    assert not auth_service.security.verify_password(
        "loser password", winner["password_hash"]
    )
    assert winner["full_name"] == "Winner Name"
    assert len(outbox) == 1


def test_code_issuance_rechecks_verification_status_in_repository(
    api, repo, outbox, clock
):
    _signup(api)
    stale_user = dict(repo.get_user_by_email("person@example.com"))
    code = outbox[0]["code"]
    assert api.post(
        "/auth/verify-email", json={"email": EMAIL, "code": code}
    ).status_code == 200
    clock.advance(61)

    pending = auth_service.issue_code(
        stale_user, auth_service.security.PURPOSE_VERIFY_EMAIL
    )

    assert pending is None
    assert len(repo.codes) == 1


def test_signup_reraises_unrelated_integrity_error(repo, monkeypatch):
    failure = db.IntegrityError("insert", {}, Exception("unrelated constraint"))

    monkeypatch.setattr(repo, "get_user_by_email", lambda email: None)
    monkeypatch.setattr(repo, "create_user", lambda *args: (_ for _ in ()).throw(failure))
    monkeypatch.setattr(db, "is_unique_violation", lambda exc, constraint: False)

    with pytest.raises(db.IntegrityError) as raised:
        auth_service.signup(EMAIL, PASSWORD, None)
    assert raised.value is failure


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


# ------------------------------------- AUTH_REQUIRE_EMAIL_VERIFICATION


@pytest.fixture
def no_verification(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)


def test_verification_is_required_by_default():
    assert settings.AUTH_REQUIRE_EMAIL_VERIFICATION is True


def test_signup_with_verification_required_sets_no_cookie_and_login_is_403(
    api, repo, outbox, monkeypatch
):
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", True)

    signup = _signup(api)
    login = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert signup.status_code == 201
    assert signup.json() == {"email": "person@example.com", "verification_required": True}
    assert SESSION_COOKIE_NAME not in signup.cookies
    assert "set-cookie" not in signup.headers
    assert login.status_code == 403
    assert login.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert SESSION_COOKIE_NAME not in login.cookies


def test_signup_without_verification_logs_in_and_sends_nothing(
    api, repo, outbox, no_verification
):
    response = _signup(api, full_name="  Test Person ")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "person@example.com"
    assert body["verification_required"] is False
    assert set(body["user"]) == {"id", "email", "full_name", "is_admin", "email_verified"}
    assert body["user"]["email"] == "person@example.com"
    assert body["user"]["full_name"] == "Test Person"
    assert body["user"]["email_verified"] is False

    set_cookie = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert f"max-age={settings.AUTH_SESSION_TTL_SECONDS}" in set_cookie

    user = repo.get_user_by_email("person@example.com")
    assert user["email_verified_at"] is None
    assert user["password_hash"].startswith("$2")
    assert outbox == []
    assert repo.codes == []


def test_signup_without_verification_cookie_works_on_session(api, no_verification):
    _signup(api)

    response = api.get("/auth/session")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert response.json()["user"]["email_verified"] is False


def test_signup_without_verification_still_validates_input(api, repo, no_verification):
    assert _signup(api, password="short").json()["error"]["code"] == "VALIDATION_ERROR"
    assert _signup(api, full_name="x").status_code == 400
    assert _signup(api, email="not-an-email").status_code == 400
    assert repo.users == {}


def test_signup_without_verification_rejects_existing_unverified_email(
    api, repo, outbox, no_verification
):
    first = _signup(api, password="first password")
    api.cookies.clear()

    second = _signup(api, password="second password")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert SESSION_COOKIE_NAME not in second.cookies
    assert "set-cookie" not in second.headers
    assert len(repo.users) == 1
    # The existing account keeps its password; nobody is logged into it.
    assert auth_service.security.verify_password(
        "first password", repo.get_user_by_email("person@example.com")["password_hash"]
    )
    assert outbox == []


def test_signup_without_verification_rejects_existing_verified_email(
    api, repo, outbox, monkeypatch
):
    _verified_user(api, outbox)
    api.cookies.clear()
    outbox.clear()
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)

    response = _signup(api, "person@example.com", password="another password")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert "set-cookie" not in response.headers
    assert auth_service.security.verify_password(
        PASSWORD, repo.get_user_by_email("person@example.com")["password_hash"]
    )
    assert outbox == []


def test_signup_without_verification_race_is_a_409(api, repo, no_verification, monkeypatch):
    def lose_race(email, password_hash, full_name):
        raise db.IntegrityError("insert", {}, Exception("duplicate"))

    monkeypatch.setattr(repo, "create_user", lose_race)
    monkeypatch.setattr(db, "is_unique_violation", lambda exc, constraint: True)

    response = _signup(api)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_signup_without_verification_reraises_unrelated_integrity_error(
    repo, no_verification, monkeypatch
):
    failure = db.IntegrityError("insert", {}, Exception("not a duplicate email"))

    def fail_create(email, password_hash, full_name):
        raise failure

    monkeypatch.setattr(repo, "create_user", fail_create)
    monkeypatch.setattr(db, "is_unique_violation", lambda exc, constraint: False)

    with pytest.raises(db.IntegrityError) as raised:
        auth_service.signup_without_verification(EMAIL, PASSWORD, None)
    assert raised.value is failure


def test_login_unverified_user_without_verification_gets_cookie_and_no_code(
    api, repo, outbox, no_verification
):
    _signup(api)
    api.cookies.clear()

    response = api.post("/auth/login", json={"email": "PERSON@example.com", "password": PASSWORD})

    assert response.status_code == 200
    assert SESSION_COOKIE_NAME in response.cookies
    assert response.json()["user"]["email_verified"] is False
    assert outbox == []
    assert repo.codes == []


def test_login_wrong_password_without_verification_is_401(api, outbox, no_verification):
    _signup(api)
    api.cookies.clear()

    response = api.post("/auth/login", json={"email": EMAIL, "password": "wrong password"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert SESSION_COOKIE_NAME not in response.cookies
    assert outbox == []


def test_switching_verification_back_on_blocks_unverified_login(api, outbox, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)
    _signup(api)
    api.cookies.clear()
    monkeypatch.setattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", True)

    response = api.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert len(outbox) == 1  # today's behaviour: a fresh code is emailed


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
