"""Exercise a running local stack exclusively through Next.js, except S3 download.

Run: backend/.venv/Scripts/python scripts/e2e_local.py --backend-log <uvicorn-log>
Requires SMTP_HOST empty and AUTH_COOKIE_SECURE=false on the local backend.
"""
from __future__ import annotations

import argparse
import io
import re
import time
import uuid
from pathlib import Path

import requests
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-log", type=Path, required=True)
    args = parser.parse_args()
    base = "http://127.0.0.1:3000"
    email = f"e2e-{uuid.uuid4().hex[:12]}@example.com"
    password = "E2e-original-password-123!"
    new_password = "E2e-updated-password-456!"
    client = requests.Session()

    def call(method: str, path: str, expected: int = 200, **kwargs):
        response = client.request(method, base + path, timeout=60, **kwargs)
        assert response.status_code == expected, (path, response.status_code, response.text)
        return response

    def code(purpose: str) -> str:
        pattern = rf"{purpose} code for {re.escape(email)} is (\d{{6}})"
        for _ in range(100):
            matches = re.findall(pattern, args.backend_log.read_text(encoding="utf-8", errors="replace"))
            if matches:
                return matches[-1]
            time.sleep(0.1)
        raise AssertionError(f"No {purpose} code in backend log")

    call("POST", "/api/auth/signup", 201, json={"email": email, "password": password, "full_name": "Local E2E"})
    print("1. PASS POST /api/auth/signup -> 201", flush=True)
    verification_code = code("verify_email")
    print("2. PASS verification code read from backend log (redacted)", flush=True)
    response = call("POST", "/api/auth/verify-email", json={"email": email, "code": verification_code})
    cookie = response.headers.get("Set-Cookie", "")
    assert "trendy_session=" in cookie and "HttpOnly" in cookie and "trendy_session" in client.cookies
    print("3. PASS POST /api/auth/verify-email -> 200; trendy_session HttpOnly Set-Cookie reaches client through Next proxy", flush=True)
    call("GET", "/dashboard", allow_redirects=False)
    print("4. PASS GET /dashboard with cookie -> 200, no redirect", flush=True)
    response = requests.get(base + "/dashboard", allow_redirects=False, timeout=60)
    assert response.status_code in (302, 303, 307, 308) and "/login" in response.headers.get("Location", ""), (response.status_code, response.headers)
    print(f"5. PASS GET /dashboard without cookie -> {response.status_code}, redirects to /login", flush=True)
    response = call("GET", "/api/auth/session")
    assert response.json()["user"]["email"] == email
    print("6. PASS GET /api/auth/session -> 200; correct verified user", flush=True)
    brand = call("POST", "/api/brands", 201, json={"name": "E2E Logo Brand"}).json()
    image = io.BytesIO()
    Image.new("RGB", (32, 32), (30, 120, 180)).save(image, format="PNG")
    response = call("POST", f"/api/brands/{brand['id']}/logo", files={"file": ("logo.png", image.getvalue(), "image/png")})
    logo_url = response.json()["logo_url"]
    assert logo_url.startswith("http://127.0.0.1:9000/brand-assets/")
    downloaded = requests.get(logo_url, timeout=30)
    assert downloaded.status_code == 200
    Image.open(io.BytesIO(downloaded.content)).verify()
    print("7. PASS POST /api/brands -> 201; POST /api/brands/{id}/logo -> 200; anonymous GET logo_url from S3 -> 200, valid image", flush=True)
    call("POST", "/api/auth/logout", 204)
    call("GET", "/api/auth/session", 401)
    print("8. PASS POST /api/auth/logout -> 204; GET /api/auth/session -> 401", flush=True)
    call("POST", "/api/auth/forgot-password", json={"email": email})
    print("9a. PASS POST /api/auth/forgot-password -> 200; reset code read from backend log (redacted)", flush=True)
    reset_code = code("reset_password")
    response = call("POST", "/api/auth/verify-reset-code", json={"email": email, "code": reset_code})
    print("9b. PASS POST /api/auth/verify-reset-code -> 200; reset_token returned", flush=True)
    call("POST", "/api/auth/reset-password", json={"reset_token": response.json()["reset_token"], "password": new_password})
    print("9c. PASS POST /api/auth/reset-password -> 200", flush=True)
    call("POST", "/api/auth/login", 401, json={"email": email, "password": password})
    print("9d. PASS POST /api/auth/login with old password -> 401", flush=True)
    call("POST", "/api/auth/login", json={"email": email, "password": new_password})
    assert call("GET", "/api/auth/session").json()["user"]["email"] == email
    call("GET", "/dashboard", allow_redirects=False)
    print("9e. PASS POST /api/auth/login with new password -> 200; session -> 200; dashboard -> 200", flush=True)
    print("SKIP image generation: requires a real OpenAI API key", flush=True)
    print("ALL END-TO-END CHECKS PASSED (all app requests used http://127.0.0.1:3000)", flush=True)


if __name__ == "__main__":
    main()
