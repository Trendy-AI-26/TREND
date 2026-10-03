from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import product_asset_loader


USER_ID = "user-123"
BRAND_ID = UUID("11111111-1111-1111-1111-111111111111")
ASSET_ID = UUID("22222222-2222-2222-2222-222222222222")


class FakeQuery:
    def __init__(self, data):
        self.data = data

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return SimpleNamespace(data=self.data)


class FakeStorageBucket:
    def __init__(self, content):
        self.content = content
        self.downloaded_path = None

    def download(self, path):
        self.downloaded_path = path
        return self.content


class FakeStorage:
    def __init__(self, content):
        self.bucket = FakeStorageBucket(content)

    def from_(self, bucket_name):
        assert bucket_name == "product-assets"
        return self.bucket


class FakeClient:
    def __init__(self, data, content):
        self.data = data
        self.table_calls = []
        self.storage = FakeStorage(content)

    def table(self, table_name):
        assert table_name == "product_assets"
        return FakeQuery(self.data)


def test_load_product_asset_reference_downloads_owned_asset(
    monkeypatch,
):
    row = {
        "id": str(ASSET_ID),
        "brand_id": str(BRAND_ID),
        "owner_user_id": USER_ID,
        "storage_path": "brands/brand/product-assets/image.png",
        "content_type": "image/png",
        "file_size_bytes": 100,
        "width": 512,
        "height": 512,
    }

    client = FakeClient(
        data=row,
        content=b"fake-png-bytes",
    )

    monkeypatch.setattr(
        product_asset_loader,
        "get_service_client",
        lambda: client,
    )

    reference = (
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )
    )

    assert reference.content == b"fake-png-bytes"
    assert reference.mime_type == "image/png"
    assert (
        client.storage.bucket.downloaded_path
        == "brands/brand/product-assets/image.png"
    )


def test_loader_rejects_asset_not_found(monkeypatch):
    client = FakeClient(
        data=None,
        content=b"",
    )

    monkeypatch.setattr(
        product_asset_loader,
        "get_service_client",
        lambda: client,
    )

    with pytest.raises(HTTPException) as error:
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )

    assert error.value.status_code == 404
    assert (
        error.value.detail["error"]["code"]
        == "PRODUCT_ASSET_NOT_FOUND"
    )


def test_loader_rejects_empty_storage_file(monkeypatch):
    row = {
        "id": str(ASSET_ID),
        "brand_id": str(BRAND_ID),
        "owner_user_id": USER_ID,
        "storage_path": "brands/brand/product-assets/image.png",
        "content_type": "image/png",
        "file_size_bytes": 100,
        "width": 512,
        "height": 512,
    }

    client = FakeClient(
        data=row,
        content=b"",
    )

    monkeypatch.setattr(
        product_asset_loader,
        "get_service_client",
        lambda: client,
    )

    with pytest.raises(HTTPException) as error:
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )

    assert error.value.status_code == 502
    assert (
        error.value.detail["error"]["code"]
        == "PRODUCT_ASSET_EMPTY"
    )
