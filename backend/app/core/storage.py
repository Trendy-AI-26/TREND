"""S3-compatible object storage (MinIO) helpers built on boto3.

Path-style addressing is used so MinIO works without wildcard DNS.
``S3_ENDPOINT_URL`` is the internal address the backend talks to;
``S3_PUBLIC_BASE_URL`` is what browsers use for public URLs.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Iterable

from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)

_NOT_FOUND_CODES = {"nosuchkey", "notfound", "404", "nosuchbucket", "nosuchupload"}


class StorageError(Exception):
    """Any object-storage failure."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class ObjectNotFoundError(StorageError):
    """The requested object (or bucket) does not exist."""


class ObjectExistsError(StorageError):
    """Upload refused because the object already exists (upsert disabled)."""


def _build_client(endpoint_url: str) -> Any:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


@lru_cache(maxsize=1)
def get_client() -> Any:
    """Client for server-to-storage calls (internal endpoint)."""
    return _build_client(settings.S3_ENDPOINT_URL)


@lru_cache(maxsize=1)
def _get_presign_client() -> Any:
    """Client whose endpoint is the browser-facing URL, used only to sign URLs."""
    return _build_client(settings.S3_PUBLIC_BASE_URL.rstrip("/"))


def _error_parts(exc: BaseException) -> tuple[int | None, str | None, str]:
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {})
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return status, error.get("Code"), error.get("Message") or str(exc)
    return None, None, str(exc)


def _is_not_found(status: int | None, code: str | None) -> bool:
    return status == 404 or (code or "").lower() in _NOT_FOUND_CODES


def _wrap(exc: BaseException, *, what: str) -> StorageError:
    status, code, message = _error_parts(exc)
    if _is_not_found(status, code):
        return ObjectNotFoundError(f"{what}: object not found", status=404, code=code)
    return StorageError(f"{what}: {message}", status=status, code=code)


def public_url(bucket: str, path: str) -> str:
    """Browser-facing URL of an object in a publicly readable bucket."""
    return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{bucket}/{path}"


def signed_url(bucket: str, path: str, expires_in: int = 3600) -> str:
    """Time-limited browser-facing URL for an object in a private bucket."""
    try:
        return _get_presign_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": path},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        raise _wrap(exc, what="sign url") from exc


def exists(bucket: str, path: str) -> bool:
    try:
        get_client().head_object(Bucket=bucket, Key=path)
        return True
    except ClientError as exc:
        status, code, _ = _error_parts(exc)
        if _is_not_found(status, code):
            return False
        raise _wrap(exc, what="head object") from exc
    except BotoCoreError as exc:
        raise _wrap(exc, what="head object") from exc


def upload(
    bucket: str,
    path: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    *,
    upsert: bool = True,
) -> None:
    """Store ``data`` at ``bucket/path``.

    With ``upsert=False`` an existing object is not overwritten
    (``ObjectExistsError``). S3 PUT overwrites by default, so this is a
    best-effort check; callers use unique (UUID) paths.
    """
    if not upsert and exists(bucket, path):
        raise ObjectExistsError(
            f"upload: object already exists: {bucket}/{path}", status=409, code="Exists"
        )
    try:
        get_client().put_object(
            Bucket=bucket,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise _wrap(exc, what="upload") from exc


def download(bucket: str, path: str) -> bytes:
    """Return the object's bytes; ``ObjectNotFoundError`` when it is missing."""
    try:
        response = get_client().get_object(Bucket=bucket, Key=path)
        return response["Body"].read()
    except (BotoCoreError, ClientError) as exc:
        raise _wrap(exc, what="download") from exc


def remove(bucket: str, paths: Iterable[str]) -> None:
    """Delete objects.

    Raises ``ObjectNotFoundError`` when the storage reports that an object (or
    the bucket) does not exist, and ``StorageError`` for any other failure.
    Callers that tolerate already-missing objects catch ``ObjectNotFoundError``.
    """
    keys = [{"Key": path} for path in paths]
    if not keys:
        return
    try:
        response = get_client().delete_objects(
            Bucket=bucket,
            Delete={"Objects": keys, "Quiet": True},
        )
    except (BotoCoreError, ClientError) as exc:
        raise _wrap(exc, what="remove") from exc

    errors = response.get("Errors") or []
    if not errors:
        return
    not_found = [e for e in errors if _is_not_found(None, e.get("Code"))]
    if len(not_found) == len(errors):
        raise ObjectNotFoundError("remove: object not found", status=404, code=errors[0].get("Code"))
    first = errors[0]
    raise StorageError(
        f"remove: {first.get('Message') or first.get('Code')}",
        code=first.get("Code"),
    )
