"""Exercise the runner guard without importing its CLI or touching live services."""

import ast
import io
import json
import time
from email import policy
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image
from starlette.testclient import _TestClientTransport
from storage3 import SyncStorageClient


@pytest.fixture
def guard():
    path = Path(__file__).resolve().parents[2] / "scripts/mvp-generation-smoke.py"
    tree = ast.parse(path.read_text())
    names = {
        "SafetyError",
        "require",
        "object_path",
        "validate_png_upload",
        "guard",
        "capture",
        "send",
        "async_send",
    }
    # Extract actual function bodies; do not execute CLI, credentials, or live probes.
    definitions = ast.Module(
        body=[
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name in names
        ],
        type_ignores=[],
    )
    namespace = {
        "httpx": httpx,
        "io": io,
        "Image": Image,
        "json": json,
        "time": time,
        "BytesParser": BytesParser,
        "policy": policy,
        "_TestClientTransport": _TestClientTransport,
        "deadline": None,
        "live_writes": True,
        "blocked": [],
        "args": SimpleNamespace(mode="run"),
        "HOST": "mdxeyhpffhijzcdjjlqe.supabase.co",
        "m": {
            "brand": "11111111-1111-4111-8111-111111111111",
            "generation": "22222222-2222-4222-8222-222222222222",
        },
        "original_send": httpx.Client.send,
        "original_async_send": httpx.AsyncClient.send,
    }
    # Trusted repository definitions only; avoids executing the live CLI bootstrap.
    exec(compile(definitions, str(path), "exec"), namespace)  # noqa: S102
    return namespace


def png():
    content = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(content, format="PNG")
    return content.getvalue()


def upload(
    guard, *, content=None, mime="image/png", filename=None, name="file", extra=False
):
    expected = guard["object_path"]()
    files = [
        (
            name,
            (
                filename or expected.rsplit("/", 1)[1],
                png() if content is None else content,
                mime,
            ),
        )
    ]
    if extra:
        files.append(("file", ("extra.png", png(), "image/png")))
    return httpx.Request(
        "POST",
        f"https://{guard['HOST']}/storage/v1/object/brand-assets/{expected}",
        files=files,
    )


def test_installed_sdk_upload_passes_guard_and_preserves_bytes(guard, monkeypatch):
    reached = []

    def transport(request):
        reached.append(request.content)
        assert request.headers["content-type"].startswith("multipart/form-data;")
        return httpx.Response(
            200, json={"Key": "brand-assets/" + guard["object_path"]()}
        )

    monkeypatch.setattr(httpx.Client, "send", guard["send"])
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        sdk = SyncStorageClient(
            f"https://{guard['HOST']}/storage/v1/", {}, http_client=client
        )
        result = sdk.from_("brand-assets").upload(
            guard["object_path"](),
            png(),
            {"content-type": "image/png", "upsert": "false"},
        )
    assert result.path == guard["object_path"]()
    assert len(reached) == 1 and png() in reached[0]


@pytest.mark.parametrize(
    "options",
    [
        {"mime": "image/jpeg"},
        {"content": b"not a PNG"},
        {"content": b""},
        {"content": b"\x89PNG\r\n\x1a\ntruncated"},
        {"content": b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024)},
        {"filename": "foreign.png"},
        {"filename": "../22222222-2222-4222-8222-222222222222.png"},
        {"name": "avatar"},
        {"extra": True},
    ],
)
def test_invalid_file_parts_rejected(guard, options):
    with pytest.raises(guard["SafetyError"]):
        guard["guard"](upload(guard, **options), None)


@pytest.mark.parametrize(
    "mutation",
    [
        "bucket",
        "object",
        "query",
        "external",
        "paid",
        "http",
        "port",
        "upsert",
        "missing_boundary",
        "truncated",
        "extra_field",
        "duplicate_header",
        "raw_png",
    ],
)
def test_bad_envelopes_and_destinations_rejected(guard, mutation):
    request = upload(guard)
    body = request.read()
    headers = dict(request.headers)
    url = str(request.url)
    if mutation == "bucket":
        url = url.replace("/brand-assets/", "/product-assets/")
    elif mutation == "object":
        url = url.replace(
            "22222222-2222-4222-8222-222222222222",
            "33333333-3333-4333-8333-333333333333",
        )
    elif mutation == "query":
        url += "?redirect=https://api.openai.com"
    elif mutation in ("external", "paid"):
        url = url.replace(
            guard["HOST"],
            "example.invalid" if mutation == "external" else "api.openai.com",
        )
    elif mutation == "http":
        url = url.replace("https:", "http:")
    elif mutation == "port":
        url = url.replace(guard["HOST"], guard["HOST"] + ":8443")
    elif mutation == "upsert":
        headers["x-upsert"] = "true"
    elif mutation == "missing_boundary":
        headers["content-type"] = "multipart/form-data"
    elif mutation == "truncated":
        body = body[:-8]
    elif mutation == "extra_field":
        marker = body.split(b"\r\n", 1)[0]
        body = (
            marker
            + b'\r\nContent-Disposition: form-data; name="metadata"\r\n\r\n{}\r\n'
            + body
        )
    elif mutation == "duplicate_header":
        body = body.replace(
            b"Content-Type: image/png",
            b"Content-Type: image/png\r\nContent-Type: image/jpeg",
        )
    elif mutation == "raw_png":
        headers["content-type"] = "image/png"
        body = png()
    headers["content-length"] = str(len(body))
    request = httpx.Request("POST", url, headers=headers, content=body)
    with pytest.raises(guard["SafetyError"]):
        guard["guard"](request, None)


def test_oversize_stream_is_stopped_before_transport(guard):
    request = upload(guard)
    request.stream = iter([b"x" * (5 * 1024 * 1024 + 16385)])
    with pytest.raises(guard["SafetyError"]):
        guard["guard"](request, None)


def test_rejected_upload_never_reaches_transport(guard, monkeypatch):
    reached = []
    monkeypatch.setattr(httpx.Client, "send", guard["send"])
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: reached.append(request))
    ) as client, pytest.raises(guard["SafetyError"]):
        client.send(upload(guard, mime="text/html"))
    assert reached == []


def test_redirect_is_rejected_and_never_followed(guard, monkeypatch):
    reached = []

    def transport(request):
        reached.append(str(request.url))
        return httpx.Response(
            307, headers={"location": "https://api.openai.com/v1/images/generations"}
        )

    monkeypatch.setattr(httpx.Client, "send", guard["send"])
    with httpx.Client(
        transport=httpx.MockTransport(transport), follow_redirects=True
    ) as client, pytest.raises(guard["SafetyError"]):
        client.send(upload(guard))
    assert len(reached) == 1 and guard["HOST"] in reached[0]


@pytest.mark.asyncio
async def test_async_paid_provider_blocked_before_transport(guard, monkeypatch):
    reached = []
    monkeypatch.setattr(httpx.AsyncClient, "send", guard["async_send"])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: reached.append(request))
    ) as client:
        with pytest.raises(guard["SafetyError"]):
            await client.post("https://api.openai.com/v1/images/generations")
    assert reached == []


@pytest.mark.parametrize("replacement", [
    b'Content-Disposition: form-data; name="file"; name="other"; filename="22222222-2222-4222-8222-222222222222.png"',
    b'Content-Disposition: form-data; name="file"; filename="22222222-2222-4222-8222-222222222222.png"; filename="foreign.png"',
])
def test_ambiguous_disposition_parameters_rejected(guard, replacement):
    request = upload(guard)
    body = request.read()
    original = body.split(b"\r\n")[1]
    body = body.replace(original, replacement)
    headers = dict(request.headers)
    headers["content-length"] = str(len(body))
    with pytest.raises(guard["SafetyError"]):
        guard["guard"](httpx.Request("POST", request.url, headers=headers, content=body), None)


def test_valid_png_at_bucket_size_limit(guard):
    import struct
    import zlib
    content = png()
    # Valid unknown ancillary PNG chunk: no decompressed-text size side effects.
    padding = b"x" * (5 * 1024 * 1024 - len(content) - 12)
    chunk = struct.pack(">I", len(padding)) + b"npAD" + padding
    chunk += struct.pack(">I", zlib.crc32(b"npAD" + padding))
    content = content[:-12] + chunk + content[-12:]
    assert len(content) == 5 * 1024 * 1024
    guard["guard"](upload(guard, content=content), None)


def test_write_approval_guard_still_required(guard):
    guard["live_writes"] = False
    with pytest.raises(guard["SafetyError"]):
        guard["guard"](upload(guard), None)
