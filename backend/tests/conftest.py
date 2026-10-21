import os

import pytest
from fastapi.testclient import TestClient

# Set required env vars before importing the app. Plain assignment (not
# setdefault) so a developer's shell or .env cannot change test behaviour.
TEST_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+psycopg://test:test@127.0.0.1:5432/test",
    "RUN_MIGRATIONS_ON_STARTUP": "false",
    "AUTH_JWT_SECRET": "test-jwt-secret-with-at-least-32-bytes-of-length",
    "AUTH_SESSION_TTL_SECONDS": "604800",
    "AUTH_COOKIE_SECURE": "false",
    "APP_ENCRYPTION_KEY": "n7Kzm1oSSOZEE5XDR6wPDfIm4CBrrq6xOS_4_T7C70Y=",
    "S3_ENDPOINT_URL": "http://127.0.0.1:9000",
    "S3_REGION": "us-east-1",
    "S3_ACCESS_KEY_ID": "test-access-key",
    "S3_SECRET_ACCESS_KEY": "test-secret-key",
    "S3_PUBLIC_BASE_URL": "https://s3.example.test",
    "SMTP_HOST": "",
    "ADMIN_EMAILS": "",
}
os.environ.update(TEST_ENV)

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
