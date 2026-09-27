"""Manual Sprint 4 provider smoke test.

Run from backend/:
    python scripts/smoke_managed_provider.py --skip-storage
    python scripts/smoke_managed_provider.py

This script is intentionally not part of the normal pytest suite. It calls
external providers and may consume API credits. It never prints API keys.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv
from PIL import Image
from supabase import ClientOptions, create_client


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
OUTPUT_DIR = BACKEND_DIR / "smoke-test-output"
IMAGE_OUTPUT = OUTPUT_DIR / "managed-image.png"
REPORT_OUTPUT = OUTPUT_DIR / "managed-provider-report.txt"


def load_environment() -> None:
    # The backend settings use backend/.env. Loading explicitly makes the
    # script independent of the directory from which it is invoked.
    load_dotenv(BACKEND_DIR / ".env", override=False)


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def check_config() -> dict[str, Any]:
    enabled = optional("MANAGED_GENERATION_ENABLED", "false").lower() == "true"
    image_provider = optional("MANAGED_IMAGE_PROVIDER", "openai")
    image_model = required("MANAGED_IMAGE_MODEL")
    image_key = required("MANAGED_IMAGE_API_KEY")
    text_provider = optional("MANAGED_TEXT_PROVIDER", "openai")
    text_model = required("MANAGED_TEXT_MODEL")
    text_key = required("MANAGED_TEXT_API_KEY")

    if not enabled:
        raise RuntimeError(
            "MANAGED_GENERATION_ENABLED is false. Set it to true in backend/.env."
        )
    if image_provider != "openai":
        raise RuntimeError(f"This script currently supports image provider openai, not {image_provider!r}.")
    if text_provider != "openai":
        raise RuntimeError(f"This script currently supports text provider openai, not {text_provider!r}.")

    return {
        "enabled": enabled,
        "image_provider": image_provider,
        "image_model": image_model,
        "image_key": image_key,
        "text_provider": text_provider,
        "text_model": text_model,
        "text_key": text_key,
    }


def openai_base_url() -> str:
    return optional("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")


def find_image_result(response_json: dict[str, Any]) -> tuple[str, str | None]:
    """Extract base64 image result from a Responses API image tool result."""
    for item in response_json.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"], item.get("id")

    # Also support the direct Images API shape so the script can diagnose both
    # adapters while the project migrates from BYOK to managed generation.
    data = response_json.get("data", [])
    if data and data[0].get("b64_json"):
        return data[0]["b64_json"], None

    raise RuntimeError(
        "Provider returned no image result. Expected output[].result or data[0].b64_json."
    )


def generate_image(config: dict[str, Any]) -> tuple[bytes, str | None, str]:
    """Generate an image through the Responses API image_generation tool."""
    url = f"{openai_base_url()}/responses"
    payload = {
        # A mainline model orchestrates the tool; the image model is explicit.
        # This follows the current Responses API image-generation contract.
        "model": optional("MANAGED_IMAGE_ORCHESTRATOR_MODEL", "gpt-5-mini"),
        "input": (
            "Generate one square product image for a social media brand. "
            "Show a premium iced coffee on a clean warm background, editorial style, "
            "soft natural light, no words, no logos, no watermark."
        ),
        "tools": [
            {
                "type": "image_generation",
                "model": config["image_model"],
                "size": "1024x1024",
                "quality": "low",
                "output_format": "png",
                "background": "opaque",
                "action": "generate",
            }
        ],
        "tool_choice": {"type": "image_generation"},
    }

    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {config['image_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    request_id = response.headers.get("x-request-id")
    if response.status_code >= 400:
        raise RuntimeError(
            f"Image provider failed: HTTP {response.status_code}; "
            f"request_id={request_id or 'unavailable'}; body={response.text[:500]}"
        )

    encoded, image_call_id = find_image_result(response.json())
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError("Image result was not valid base64.") from exc

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_OUTPUT.write_bytes(image_bytes)

    try:
        with Image.open(IMAGE_OUTPUT) as image:
            image.verify()
    except Exception as exc:
        raise RuntimeError("Generated bytes are not a valid image file.") from exc

    return image_bytes, request_id or image_call_id, response.headers.get("x-request-id") or ""


def generate_caption(config: dict[str, Any]) -> tuple[str, str | None]:
    """Generate a minimal caption through the Responses API."""
    url = f"{openai_base_url()}/responses"
    payload = {
        "model": config["text_model"],
        "input": (
            "Write one short Arabic Instagram caption for a premium iced coffee launch. "
            "Return plain text only, without JSON, markdown, or quotation marks."
        ),
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {config['text_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    request_id = response.headers.get("x-request-id")
    if response.status_code >= 400:
        raise RuntimeError(
            f"Caption provider failed: HTTP {response.status_code}; "
            f"request_id={request_id or 'unavailable'}; body={response.text[:500]}"
        )

    data = response.json()
    caption = str(data.get("output_text", "")).strip()
    if not caption:
        # Defensive fallback for compatible Responses API shapes.
        parts: list[str] = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"} and content.get("text"):
                    parts.append(str(content["text"]))
        caption = " ".join(parts).strip()

    if not caption:
        raise RuntimeError("Caption provider returned an empty response.")
    return caption, request_id


def storage_check(image_bytes: bytes) -> tuple[str, str]:
    """Upload an isolated temporary object, verify signed URL, then remove it."""
    supabase_url = required("SUPABASE_URL")
    supabase_secret = required("SUPABASE_SECRET_KEY")
    bucket = optional("STORAGE_BUCKET", "brand-assets")
    path = f"smoke-tests/{uuid.uuid4()}/managed-image.png"

    client = create_client(
        supabase_url,
        supabase_secret,
        options=ClientOptions(postgrest_client_timeout=30, storage_client_timeout=60),
    )
    storage = client.storage.from_(bucket)

    try:
        storage.upload(
            path,
            image_bytes,
            {"content-type": "image/png", "upsert": "false"},
        )

        signed = storage.create_signed_url(path, 300)
        signed_url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
        if not signed_url:
            raise RuntimeError(f"Storage returned no signed URL: {signed}")

        with httpx.Client(timeout=30.0) as http:
            downloaded = http.get(signed_url)
            downloaded.raise_for_status()
        if not downloaded.content:
            raise RuntimeError("Signed URL returned an empty response.")
        with Image.open(__import__("io").BytesIO(downloaded.content)) as image:
            image.verify()
        return bucket, path
    finally:
        try:
            storage.remove([path])
        except Exception as cleanup_error:
            print(f"WARNING: cleanup failed for {bucket}/{path}: {cleanup_error}")


def write_report(lines: list[str]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Sprint 4 managed provider smoke test.")
    parser.add_argument(
        "--skip-storage",
        action="store_true",
        help="Do not upload to Supabase Storage; image and caption checks still run.",
    )
    args = parser.parse_args()

    load_environment()
    report: list[str] = [
        "Sprint 4 Managed Provider Smoke Test",
        f"Image output: {IMAGE_OUTPUT}",
    ]

    try:
        config = check_config()
        print("[PASS] managed configuration loaded (keys are not printed)")
        print(f"[INFO] image model: {config['image_model']}")
        print(f"[INFO] text model: {config['text_model']}")
        report += [
            "Configuration: PASS",
            f"Image model: {config['image_model']}",
            f"Text model: {config['text_model']}",
        ]

        image_bytes, image_request_id, _ = generate_image(config)
        print(f"[PASS] image generated and validated ({len(image_bytes)} bytes)")
        print(f"[INFO] image request id: {image_request_id or 'unavailable'}")
        report += [
            "Image generation: PASS",
            f"Image bytes: {len(image_bytes)}",
            f"Image request id: {image_request_id or 'unavailable'}",
            "Image validation: PASS",
        ]

        if args.skip_storage:
            print("[SKIP] storage upload (--skip-storage)")
            report.append("Storage upload: SKIPPED")
        else:
            bucket, path = storage_check(image_bytes)
            print(f"[PASS] storage upload, signed URL retrieval, and cleanup: {bucket}/{path}")
            report += [
                "Storage upload: PASS",
                "Signed URL retrieval: PASS",
                "Temporary object cleanup: PASS",
            ]

        caption, caption_request_id = generate_caption(config)
        print(f"[PASS] caption generated ({len(caption)} characters)")
        print(f"[INFO] caption request id: {caption_request_id or 'unavailable'}")
        report += [
            "Caption generation: PASS",
            f"Caption request id: {caption_request_id or 'unavailable'}",
            f"Caption preview: {caption[:120]}",
        ]

        report.append("Overall: PASS" if not args.skip_storage else "Overall: PASS (storage skipped)")
        write_report(report)
        print(f"[PASS] report written to {REPORT_OUTPUT}")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        report.append(f"Overall: BLOCKED — {exc}")
        try:
            write_report(report)
            print(f"[INFO] partial report written to {REPORT_OUTPUT}", file=sys.stderr)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
