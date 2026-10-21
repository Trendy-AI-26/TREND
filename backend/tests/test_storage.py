from urllib.parse import urlparse

import pytest
from botocore.exceptions import ClientError

from app.config import settings
from app.core import storage


def _client_error(code: str, status: int, operation: str = "GetObject") -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": code}, "ResponseMetadata": {"HTTPStatusCode": status}},
        operation,
    )


class FakeS3:
    def __init__(self):
        self.objects: dict[tuple[str, str], bytes] = {}
        self.put_calls = []
        self.delete_errors = []
        self.raise_on_delete = None

    def put_object(self, Bucket, Key, Body, ContentType):
        self.put_calls.append((Bucket, Key, ContentType))
        self.objects[(Bucket, Key)] = Body

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise _client_error("404", 404, "HeadObject")

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise _client_error("NoSuchKey", 404)

        class Body:
            def __init__(self, data):
                self.data = data

            def read(self):
                return self.data

        return {"Body": Body(self.objects[(Bucket, Key)])}

    def delete_objects(self, Bucket, Delete):
        if self.raise_on_delete:
            raise self.raise_on_delete
        for item in Delete["Objects"]:
            self.objects.pop((Bucket, item["Key"]), None)
        return {"Errors": self.delete_errors} if self.delete_errors else {}


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(storage, "get_client", lambda: fake)
    return fake


def test_public_url_uses_public_base_url_bucket_and_path(monkeypatch):
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://s3.example.com")

    assert (
        storage.public_url("brand-assets", "brands/abc/logo.png")
        == "https://s3.example.com/brand-assets/brands/abc/logo.png"
    )


def test_public_url_ignores_trailing_slash_on_base(monkeypatch):
    monkeypatch.setattr(settings, "S3_PUBLIC_BASE_URL", "https://s3.example.com/")

    assert storage.public_url("avatars", "a/b.png") == "https://s3.example.com/avatars/a/b.png"


def test_public_url_uses_configured_bucket_names():
    url = storage.public_url(settings.STORAGE_BUCKET, "brands/x/generations/y.png")

    assert url == f"{settings.S3_PUBLIC_BASE_URL}/brand-assets/brands/x/generations/y.png"


def test_signed_url_points_at_the_public_host_with_a_signature():
    storage._get_presign_client.cache_clear()
    url = storage.signed_url("product-assets", "brands/x/product-assets/y.png", 600)

    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}" == settings.S3_PUBLIC_BASE_URL
    # Path-style addressing: bucket is the first path segment, not a subdomain.
    assert parsed.path == "/product-assets/brands/x/product-assets/y.png"
    assert "X-Amz-Signature=" in parsed.query
    assert "X-Amz-Expires=600" in parsed.query


def test_upload_download_roundtrip(s3):
    storage.upload("brand-assets", "a/b.png", b"data", "image/png")

    assert s3.put_calls == [("brand-assets", "a/b.png", "image/png")]
    assert storage.download("brand-assets", "a/b.png") == b"data"


def test_upload_without_upsert_refuses_to_overwrite(s3):
    storage.upload("b", "k", b"1", "image/png", upsert=False)

    with pytest.raises(storage.ObjectExistsError):
        storage.upload("b", "k", b"2", "image/png", upsert=False)

    assert s3.objects[("b", "k")] == b"1"
    storage.upload("b", "k", b"3", "image/png", upsert=True)
    assert s3.objects[("b", "k")] == b"3"


def test_download_of_missing_object_raises_not_found(s3):
    with pytest.raises(storage.ObjectNotFoundError) as error:
        storage.download("b", "missing")

    assert error.value.status == 404


def test_download_other_failures_are_storage_errors(s3, monkeypatch):
    def boom(Bucket, Key):
        raise _client_error("InternalError", 500)

    monkeypatch.setattr(s3, "get_object", boom)

    with pytest.raises(storage.StorageError) as error:
        storage.download("b", "k")

    assert not isinstance(error.value, storage.ObjectNotFoundError)
    assert error.value.status == 500


def test_remove_deletes_objects_and_ignores_empty_input(s3):
    s3.objects[("b", "k")] = b"x"

    storage.remove("b", [])
    storage.remove("b", ["k"])

    assert ("b", "k") not in s3.objects


def test_remove_maps_missing_object_to_not_found(s3):
    s3.delete_errors = [{"Key": "k", "Code": "NoSuchKey", "Message": "gone"}]

    with pytest.raises(storage.ObjectNotFoundError):
        storage.remove("b", ["k"])


def test_remove_maps_missing_bucket_to_not_found(s3):
    s3.raise_on_delete = _client_error("NoSuchBucket", 404, "DeleteObjects")

    with pytest.raises(storage.ObjectNotFoundError):
        storage.remove("b", ["k"])


def test_remove_other_failures_are_storage_errors(s3):
    s3.delete_errors = [{"Key": "k", "Code": "AccessDenied", "Message": "denied"}]

    with pytest.raises(storage.StorageError) as error:
        storage.remove("b", ["k"])

    assert not isinstance(error.value, storage.ObjectNotFoundError)

    s3.delete_errors = []
    s3.raise_on_delete = _client_error("SlowDown", 503, "DeleteObjects")
    with pytest.raises(storage.StorageError) as error:
        storage.remove("b", ["k"])
    assert error.value.status == 503


def test_client_uses_path_style_addressing_and_internal_endpoint():
    storage.get_client.cache_clear()
    client = storage.get_client()

    assert client.meta.endpoint_url == settings.S3_ENDPOINT_URL
    assert client.meta.config.s3["addressing_style"] == "path"
    assert client.meta.region_name == settings.S3_REGION
    storage.get_client.cache_clear()
