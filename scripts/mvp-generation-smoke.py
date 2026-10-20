"""One-use approved MVP smoke. Setup/SQL cleanup are separately reviewed queries.

No provider credentials are used. All application writes are fixture-scoped at
the HTTP boundary. Run preflight first; run cannot be repeated with this manifest.
"""
import argparse
import asyncio
import hashlib
import io
import json
import logging
import os
from email import policy
from email.parser import BytesParser
from pathlib import Path
import sys
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")
for name in ("GENERATION_API_KEY", "MANAGED_API_KEY", "OPENAI_API_KEY"):
    os.environ[name] = "smoke-no-provider-credential"
for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(name, None)
logging.disable(logging.CRITICAL)

import httpx
from PIL import Image
from fastapi.testclient import TestClient
from starlette.testclient import _TestClientTransport
from app.config import settings
from app.core.auth import User, get_current_user
from app.core.supabase import get_service_client
from app.main import app
from app.routers import generations
from app.services.generation_resolver import ManagedGenerationConfig
from app.services.providers.base import ProviderResult

PROJECT = "mdxeyhpffhijzcdjjlqe"
HOST = PROJECT + ".supabase.co"
parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("preflight", "run", "storage-cleanup"))
parser.add_argument("manifest")
args = parser.parse_args()
manifest_path = Path(args.manifest).resolve()
m = json.loads(manifest_path.read_text())
assert m["projectRef"] == PROJECT
for key in ("run", "user", "brand"):
    UUID(m[key])
assert settings.SUPABASE_URL.rstrip("/") == "https://" + HOST
assert settings.STORAGE_BUCKET == "brand-assets"
assert settings.GENERATION_CREDIT_COST == 1
blocked = []
calls = 0
live_writes = False
deadline = None


def save():
    manifest_path.write_text(json.dumps(m, indent=2) + "\n")


def object_path():
    return f"brands/{m['brand']}/generations/{m['generation']}.png"


class SafetyError(RuntimeError):
    pass


def require(condition):
    if not condition:
        raise SafetyError("Request violates smoke fixture boundary")


def validate_png_upload(request, expected):
    """Validate the installed SDK's single-file multipart upload before transport."""
    require(request.url.raw_path == ("/storage/v1/object/brand-assets/" + expected).encode())
    require(not request.url.fragment and not request.url.username and not request.url.password)
    require(request.headers.get("x-upsert", "false") == "false")
    require(len(request.headers.get_list("content-type")) == 1)
    content_type = request.headers["content-type"]
    require("\r" not in content_type and "\n" not in content_type)
    header = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii") + b"\r\n\r\n"
    )
    require(header.get_content_type() == "multipart/form-data")
    require([key for key, _ in header.get_params()] == ["multipart/form-data", "boundary"])
    boundary = header.get_boundary()
    require(boundary is not None and 1 <= len(boundary) <= 70)
    require(all(32 <= ord(char) < 127 for char in boundary))
    # Bucket limit applies to the file, with a small separate envelope allowance.
    file_limit = 5 * 1024 * 1024
    parts, total = [], 0
    for chunk in request.stream:
        total += len(chunk)
        require(total <= file_limit + 16384)
        parts.append(chunk)
    body = b"".join(parts)
    require(request.headers.get_list("content-length") == [str(len(body))])
    require("transfer-encoding" not in request.headers)
    request.stream = httpx.ByteStream(body)
    require(request.read() == body)  # preserve the exact SDK bytes for send()
    require(body.startswith(b"--" + boundary.encode() + b"\r\n"))
    require(body.endswith(b"\r\n--" + boundary.encode() + b"--\r\n"))
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("ascii") + b"\r\n\r\n" + body
    )
    require(message.is_multipart() and not message.defects)
    require(all(not part.defects for part in message.walk()))
    require(all(not getattr(value, "defects", ()) for part in message.walk() for _, value in part.items()))
    files = list(message.iter_parts())
    require(len(files) == 1)
    part = files[0]
    require(not part.is_multipart())
    require(sorted(key.lower() for key in part.keys()) == ["content-disposition", "content-type"])
    require(part.get_content_disposition() == "form-data")
    require(sorted(key for key, _ in part.get_params(header="content-disposition")) == ["filename", "form-data", "name"])
    require(part.get_param("name", header="content-disposition") == "file")
    require(part.get_filename() == expected.rsplit("/", 1)[-1])
    require(part.get_content_type() == "image/png")
    require(part.get_params() == [("image/png", "")])
    content = part.get_payload(decode=True)
    require(isinstance(content, bytes) and 0 < len(content) <= file_limit)
    require(content.startswith(b"\x89PNG\r\n\x1a\n"))
    try:
        with Image.open(io.BytesIO(content)) as image:
            require(image.format == "PNG" and 0 < image.width <= 4096 and 0 < image.height <= 4096)
            image.verify()
    except SafetyError:
        raise
    except Exception as exc:
        raise SafetyError("Invalid PNG upload") from exc


def guard(request, transport):
    if deadline is not None:
        require(time.monotonic() < deadline)
    host, path = request.url.host, request.url.path
    if host == "testserver" and isinstance(transport, _TestClientTransport):
        return
    if host != HOST or request.url.scheme != "https" or request.url.port not in (None, 443):
        blocked.append(host)
        raise SafetyError("External destination blocked")
    require(path.startswith(("/rest/v1/", "/storage/v1/")))
    if request.method in ("GET", "HEAD"):
        return
    require(live_writes)
    data = json.loads(request.content) if "application/json" in request.headers.get("content-type", "") else None
    if path.startswith("/storage/v1/"):
        expected = object_path()
        if request.method == "POST":
            require(args.mode == "run" and path == "/storage/v1/object/brand-assets/" + expected)
            validate_png_upload(request, expected)
        elif request.method == "DELETE":
            require(args.mode == "storage-cleanup" and path == "/storage/v1/object/brand-assets")
            require(data == {"prefixes": [expected]})
        else:
            raise SafetyError("Storage operation blocked")
        return
    require(args.mode == "run")
    name = path.removeprefix("/rest/v1/")
    if name.startswith("rpc/"):
        require(request.method == "POST" and data.get("p_user_id") == m["user"])
        if name == "rpc/check_generation_rate_limit":
            require(data.get("p_bucket") == "image_generation")
            return
        require(name in {"rpc/" + verb + "_generation_" + kind for verb in ("reserve", "commit", "release") for kind in ("credit", "slot")})
        require(data.get("p_generation_id") == m["generation"])
        if name.endswith("credit"):
            require(data.get("p_amount") == 1)
            require(data.get("p_idempotency_key", data.get("p_reservation_id")) == f"generation:{m['generation']}:reserve")
        return
    params = dict(request.url.params)
    if request.method == "POST":
        require(isinstance(data, dict) and data.get("user_id") == m["user"])
        if name == "generations":
            require(m.get("generation") is None and data.get("brand_id") == m["brand"] and data.get("idempotency_key") == m["key"])
            UUID(data["id"])
            m["generation"] = data["id"]
            save()  # capture ownership before sending the write
        else:
            require(name in ("generation_locks", "idempotency_records", "usage_events"))
            require(data.get("generation_id") == m["generation"])
            if name == "idempotency_records":
                require(data.get("idempotency_key") == m["key"] and data.get("scope") == "image_generation")
    elif request.method == "PATCH":
        require(name in ("generations", "idempotency_records", "usage_events"))
        record_id = m.get("generation") if name == "generations" else m.get(name + "_id")
        require(record_id is not None and params.get("id") == "eq." + record_id)
    elif request.method == "DELETE":
        require(name in ("generation_locks", "idempotency_records", "generations"))
        if name == "generation_locks":
            require(params.get("user_id") == "eq." + m["user"] and params.get("generation_id") == "eq." + m["generation"])
        else:
            require(params.get("id") == "eq." + (m["generation"] if name == "generations" else m["idempotency_records_id"]))
    else:
        raise SafetyError("Database operation blocked")


def capture(request, response):
    require(not response.is_redirect)
    name = request.url.path.removeprefix("/rest/v1/")
    if request.method == "POST" and name in ("idempotency_records", "usage_events") and response.is_success:
        rows = response.json()
        require(len(rows) == 1 and rows[0]["user_id"] == m["user"] and rows[0]["generation_id"] == m["generation"])
        m[name + "_id"] = rows[0]["id"]
        save()
    return response


original_send = httpx.Client.send
original_async_send = httpx.AsyncClient.send


def send(self, request, **kwargs):
    guard(request, self._transport)
    kwargs["follow_redirects"] = False
    return capture(request, original_send(self, request, **kwargs))


async def async_send(self, request, **kwargs):
    guard(request, self._transport)
    kwargs["follow_redirects"] = False
    return capture(request, await original_async_send(self, request, **kwargs))


httpx.Client.send = send
httpx.AsyncClient.send = async_send


async def mock_provider(**kwargs):
    global calls
    calls += 1
    require(calls == 1)
    require(kwargs["api_key"] == "smoke-no-provider-credential")
    content = io.BytesIO()
    Image.new("RGB", (1024, 1024), (64, 128, 192)).save(content, format="PNG")
    return ProviderResult(image_bytes=content.getvalue(), request_id="mock-" + m["run"])


generations.openai_generate = mock_provider
generations.resolve_generation_config = lambda: ManagedGenerationConfig(
    provider="openai", model="mvp-smoke-mocked", api_key="smoke-no-provider-credential"
)
app.dependency_overrides[get_current_user] = lambda: User(
    id=m["user"], email=m["email"], access_token="synthetic-local-auth"
)


def safety_checks():
    global live_writes
    require(generations.openai_generate is mock_provider)
    for url in ("https://api.openai.com/v1/images/generations", "https://generativelanguage.googleapis.com/", "https://api.anthropic.com/", "https://example.invalid/"):
        try:
            httpx.post(url, timeout=1)
        except SafetyError:
            pass
        else:
            raise SafetyError("Provider network denial failed")
    async def probe():
        async with httpx.AsyncClient() as client:
            try:
                await client.post("https://api.openai.com/v1/images/generations")
            except SafetyError:
                return
            raise SafetyError("Async provider network denial failed")
    asyncio.run(probe())
    require(len(blocked) == 5 and calls == 0)
    # This must fail even on the allowed host, before reaching transport.
    try:
        guard(httpx.Request("PATCH", f"https://{HOST}/rest/v1/credit_accounts", json={"balance": 0}), None)
    except SafetyError:
        pass
    else:
        raise SafetyError("Foreign mutation denial failed")
    live_writes = True
    try:
        probes = [
            httpx.Request("PATCH", f"https://{HOST}/rest/v1/generations?id=eq.foreign", json={"status": "failed"}),
            httpx.Request("POST", f"https://{HOST}/rest/v1/rpc/commit_generation_credit", json={"p_user_id": "foreign"}),
        ]
        for request in probes:
            try:
                guard(request, None)
            except SafetyError:
                pass
            else:
                raise SafetyError("Foreign fixture guard failed")
    finally:
        live_writes = False
    get_service_client().table("generations").select("id").limit(1).execute()


def smoke():
    global live_writes, deadline
    deadline = time.monotonic() + 300
    require(m.get("approved") is True and m.get("preflight") == "PASS")
    marker = manifest_path.with_suffix(".consumed")
    with marker.open("x") as handle:
        handle.write(m["run"])
    client = get_service_client()
    brand = client.table("brands").select("*").eq("id", m["brand"]).single().execute().data
    require(brand["owner_user_id"] == m["user"] and brand["name"] == m["brandName"])
    require(client.table("generations").select("id").eq("user_id", m["user"]).execute().data == [])
    account = client.table("credit_accounts").select("balance,reserved").eq("user_id", m["user"]).single().execute().data
    require(account == {"balance": 5, "reserved": 0})
    from tests.test_generation_endpoint import VALID_BRIEF
    brief = {**VALID_BRIEF, "core_idea": "Synthetic MVP smoke test: a plain blue square", "optional_notes": "Synthetic test only", "text_to_include": "TEST"}
    body = {"brief": brief, "platform_preset": "instagram_post", "logo_mode": "none"}
    live_writes = True
    with TestClient(app) as local:
        first = local.post(f"/brands/{m['brand']}/generate", json=body, headers={"Idempotency-Key": m["key"]})
        m["first_status"] = first.status_code
        if first.status_code != 200:
            m["first_error"] = first.json()
            save()
        require(first.status_code == 200)
        first_body = first.json()
        require(first_body["status"] == "succeeded" and first_body["id"] == m["generation"])
        second = local.post(f"/brands/{m['brand']}/generate", json=body, headers={"Idempotency-Key": m["key"]})
        m["replay_status"] = second.status_code
        require(second.status_code == 200 and second.json() == first_body and calls == 1)
    live_writes = False
    data = client.storage.from_("brand-assets").download(object_path())
    with Image.open(io.BytesIO(data)) as img:
        require(img.size == (1024, 1024) and img.format == "PNG")
        img.verify()
    rows = client.table("credit_ledger").select("operation,amount").eq("user_id", m["user"]).execute().data
    require(sorted((r["operation"], r["amount"]) for r in rows) == [("commit", -1), ("grant", 5), ("reserve", 1)])
    account = client.table("credit_accounts").select("balance,reserved").eq("user_id", m["user"]).single().execute().data
    require(account == {"balance": 4, "reserved": 0})
    quota = client.table("user_generation_quotas").select("reserved,consumed").eq("user_id", m["user"]).single().execute().data
    daily = client.table("generation_daily_usage").select("reserved,consumed").eq("user_id", m["user"]).execute().data
    require(quota == {"reserved": 0, "consumed": 1} and daily == [quota])
    require(client.table("generation_quota_reservations").select("status").eq("user_id", m["user"]).execute().data == [{"status": "committed"}])
    require(client.table("generation_locks").select("user_id").eq("user_id", m["user"]).execute().data == [])
    require(len(client.table("generations").select("id").eq("user_id", m["user"]).execute().data) == 1)
    require(client.table("idempotency_records").select("status").eq("user_id", m["user"]).execute().data == [{"status": "succeeded"}])
    m.update(result="PASS", provider_calls=calls, output_sha256=hashlib.sha256(data).hexdigest(), settlement={"credit": account, "quota": quota}, identical_replay=True)


try:
    safety_checks()
    if args.mode == "preflight":
        m.update(preflight="PASS", network_block_probes=len(blocked), mock_verified=True)
    elif args.mode == "run":
        smoke()
    else:
        require(m.get("generation") is not None and m.get("approved") is False)
        live_writes = True
        get_service_client().storage.from_("brand-assets").remove([object_path()])
        live_writes = False
        m["storage_remove_requested"] = True
except Exception as exc:
    m["result"] = "FAIL"
    m["failure"] = type(exc).__name__  # no credentials or arbitrary service payload
    raise
finally:
    if args.mode == "run":
        m["approved"] = False
        m["provider_calls"] = calls
    save()
    print(json.dumps({k: m.get(k) for k in ("preflight", "result", "failure", "first_status", "replay_status", "provider_calls", "approved", "storage_remove_requested")}))
