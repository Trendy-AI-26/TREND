import logging
import smtplib

import pytest
from cryptography.fernet import Fernet

from app import config
from app.config import settings
from app.core import security, vault
from app.services import mailer


# ---------------------------------------------------------------- passwords


def test_password_hash_roundtrip_and_salting():
    first = security.hash_password("a long password")
    second = security.hash_password("a long password")

    assert first != second
    assert first.startswith("$2")
    assert security.verify_password("a long password", first)
    assert not security.verify_password("another password", first)
    assert not security.verify_password("a long password", None)
    assert not security.verify_password("a long password", "not-a-hash")


@pytest.mark.parametrize(
    ("password", "ok"),
    [("1234567", False), ("12345678", True), ("x" * 72, True), ("x" * 73, False), ("é" * 37, False)],
)
def test_password_validation(password, ok):
    assert (security.validate_password(password) is None) is ok


# -------------------------------------------------------------------- codes


def test_codes_are_six_digits():
    for _ in range(50):
        code = security.generate_code()
        assert len(code) == 6 and code.isdigit()


def test_code_hash_is_bound_to_user_and_purpose():
    digest = security.hash_code("u1", "verify_email", "123456")

    assert digest != "123456"
    assert security.code_matches("u1", "verify_email", "123456", digest)
    assert not security.code_matches("u1", "verify_email", "123457", digest)
    assert not security.code_matches("u2", "verify_email", "123456", digest)
    assert not security.code_matches("u1", "reset_password", "123456", digest)


def test_contract_constants():
    assert security.CODE_TTL_SECONDS == 15 * 60
    assert security.CODE_MAX_ATTEMPTS == 5
    assert security.CODE_RESEND_COOLDOWN_SECONDS == 60
    assert security.RESET_TOKEN_TTL_SECONDS == 15 * 60
    assert security.SESSION_COOKIE_NAME == "trendy_session"
    assert settings.AUTH_SESSION_TTL_SECONDS == 604800


# ---------------------------------------------------------- JWT secret guard


def test_missing_jwt_secret_is_an_error_in_production(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")

    with pytest.raises(RuntimeError):
        config.validate_startup_settings()
    with pytest.raises(RuntimeError):
        config.get_jwt_secret()


def test_missing_jwt_secret_only_warns_in_development(monkeypatch, caplog):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "")
    monkeypatch.setattr(settings, "APP_ENV", "development")

    with caplog.at_level(logging.WARNING, logger="app.config"):
        config.validate_startup_settings()

    assert "AUTH_JWT_SECRET" in caplog.text
    assert config.get_jwt_secret()


def test_production_with_secret_starts(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_JWT_SECRET", "s" * 40)
    monkeypatch.setattr(settings, "APP_ENV", "production")

    config.validate_startup_settings()
    assert config.get_jwt_secret() == "s" * 40


# -------------------------------------------------------------------- vault


def test_vault_encrypts_and_decrypts():
    token = vault.encrypt_secret("sk-secret-value")

    assert "sk-secret-value" not in token
    assert vault.decrypt_secret(token) == "sk-secret-value"
    assert vault.encrypt_secret("sk-secret-value") != token  # fresh IV each time


def test_vault_requires_a_key(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENCRYPTION_KEY", "")

    with pytest.raises(vault.VaultError):
        vault.encrypt_secret("x")


def test_vault_rejects_malformed_key(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENCRYPTION_KEY", "not-a-fernet-key")

    with pytest.raises(vault.VaultError):
        vault.encrypt_secret("x")


def test_vault_rejects_token_from_another_key(monkeypatch):
    token = vault.encrypt_secret("x")
    monkeypatch.setattr(settings, "APP_ENCRYPTION_KEY", Fernet.generate_key().decode())

    with pytest.raises(vault.VaultError):
        vault.decrypt_secret(token)


# ------------------------------------------------------------------- mailer


def test_message_is_short_and_bilingual():
    message = mailer.build_code_message("a@example.com", "042042", "verify_email")
    body = message.get_content()

    assert message["To"] == "a@example.com"
    assert "042042" in body
    assert "TRENDY AI" in message["Subject"]
    assert any("\u0600" <= ch <= "\u06ff" for ch in body + message["Subject"])  # Arabic
    assert "verify" in body.lower()
    assert len(body.splitlines()) < 20


def test_reset_message_mentions_password():
    body = mailer.build_code_message("a@example.com", "111111", "reset_password").get_content()

    assert "reset your password" in body


def test_without_smtp_host_the_code_is_logged_at_warning(monkeypatch, caplog):
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    called = []
    monkeypatch.setattr(mailer, "_send_sync", lambda m: called.append(m))

    with caplog.at_level(logging.WARNING, logger="app.services.mailer"):
        mailer.send_code_email_sync("a@example.com", "654321", "verify_email")

    assert called == []
    record = next(r for r in caplog.records if "654321" in r.getMessage())
    assert record.levelno == logging.WARNING


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None, **_):
        self.host, self.port = host, port
        self.calls = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, message):
        self.calls.append(("send", message["To"]))


def test_smtp_send_uses_starttls_login_and_from(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "mailer")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "pw")
    monkeypatch.setattr(settings, "SMTP_FROM", "TRENDY <no-reply@example.com>")
    monkeypatch.setattr(settings, "SMTP_STARTTLS", True)

    mailer.send_code_email_sync("a@example.com", "123456", "verify_email")

    smtp = FakeSMTP.instances[0]
    assert (smtp.host, smtp.port) == ("smtp.example.com", 587)
    assert "starttls" in smtp.calls
    assert ("login", "mailer", "pw") in smtp.calls
    assert ("send", "a@example.com") in smtp.calls
    assert smtp.calls.index("starttls") < smtp.calls.index(("login", "mailer", "pw"))


@pytest.mark.asyncio
async def test_async_send_never_raises_and_runs_in_a_thread(monkeypatch, caplog):
    import threading

    seen = {}

    def failing(to, code, purpose):
        seen["thread"] = threading.current_thread()
        raise OSError("smtp down")

    monkeypatch.setattr(mailer, "send_code_email_sync", failing)

    with caplog.at_level(logging.ERROR, logger="app.services.mailer"):
        await mailer.send_code_email("a@example.com", "123456", "verify_email")

    assert seen["thread"] is not threading.main_thread()
    assert "Failed to send" in caplog.text
