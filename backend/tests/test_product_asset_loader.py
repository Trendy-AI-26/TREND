from uuid import UUID

import pytest
from fastapi import HTTPException

from app import db
from app.core import storage
from app.services import product_asset_loader


USER_ID = "user-123"
BRAND_ID = UUID("11111111-1111-1111-1111-111111111111")
ASSET_ID = UUID("22222222-2222-2222-2222-222222222222")


def _row():
    return {
        "id": str(ASSET_ID),
        "brand_id": str(BRAND_ID),
        "owner_user_id": USER_ID,
        "storage_path": "brands/brand/product-assets/image.png",
        "content_type": "image/png",
        "file_size_bytes": 100,
        "width": 512,
        "height": 512,
    }


class FakeDb:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def fetch_one(self, sql, params=None, **_kwargs):
        self.calls.append((sql, params))
        return self.row


class FakeStorage:
    def __init__(self, content=b"", error=None):
        self.content = content
        self.error = error
        self.downloaded = None

    def download(self, bucket, path):
        self.downloaded = (bucket, path)
        if self.error:
            raise self.error
        return self.content


def _install(monkeypatch, row, content=b"", error=None):
    fake_db = FakeDb(row)
    fake_storage = FakeStorage(content, error)
    monkeypatch.setattr(db, "fetch_one", fake_db.fetch_one)
    monkeypatch.setattr(storage, "download", fake_storage.download)
    return fake_db, fake_storage


def test_load_product_asset_reference_downloads_owned_asset(monkeypatch):
    fake_db, fake_storage = _install(monkeypatch, _row(), b"fake-png-bytes")

    reference = product_asset_loader.load_product_asset_reference(
        asset_id=ASSET_ID,
        brand_id=BRAND_ID,
        user_id=USER_ID,
    )

    assert reference.content == b"fake-png-bytes"
    assert reference.mime_type == "image/png"
    assert fake_storage.downloaded == (
        "product-assets",
        "brands/brand/product-assets/image.png",
    )
    # Ownership is enforced in the query itself.
    sql, params = fake_db.calls[0]
    assert "owner_user_id" in sql
    assert params["user_id"] == USER_ID
    assert params["brand_id"] == str(BRAND_ID)


def test_loader_rejects_asset_not_found(monkeypatch):
    _install(monkeypatch, None)

    with pytest.raises(HTTPException) as error:
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )

    assert error.value.status_code == 404
    assert error.value.detail["error"]["code"] == "PRODUCT_ASSET_NOT_FOUND"


def test_loader_rejects_empty_storage_file(monkeypatch):
    _install(monkeypatch, _row(), b"")

    with pytest.raises(HTTPException) as error:
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )

    assert error.value.status_code == 502
    assert error.value.detail["error"]["code"] == "PRODUCT_ASSET_EMPTY"


def test_loader_maps_storage_failure(monkeypatch):
    _install(monkeypatch, _row(), error=storage.ObjectNotFoundError("missing"))

    with pytest.raises(HTTPException) as error:
        product_asset_loader.load_product_asset_reference(
            asset_id=ASSET_ID,
            brand_id=BRAND_ID,
            user_id=USER_ID,
        )

    assert error.value.status_code == 502
    assert error.value.detail["error"]["code"] == "PRODUCT_ASSET_READ_FAILED"
