from app import db
from app.core.auth import User
from app.routers import brands


def test_brand_list_batches_summary_and_keeps_owner_filter(monkeypatch):
    calls = []
    brand_rows = [{
        "id": "brand-1", "name": "Brand", "created_at": "2026-10-07T00:00:00Z",
    }]
    kit_rows = [{
        "brand_id": "brand-1", "status": "complete", "colors": ["#123456"],
        "industry": "Food", "tagline": "Fresh",
    }]

    def fake_fetch_all(sql, params=None, **_kwargs):
        calls.append((sql, dict(params or {})))
        if "FROM brand_kits" in sql:
            return kit_rows
        if "FROM brands" in sql:
            return brand_rows
        raise AssertionError(f"unexpected query: {sql}")

    monkeypatch.setattr(db, "fetch_all", fake_fetch_all)

    result = brands.list_brands(User(id="owner", email="test@example.com", access_token=""))

    assert result[0].colors == ["#123456"]
    assert result[0].industry == "Food"
    assert result[0].tagline == "Fresh"
    assert len(calls) == 2
    brand_sql, brand_params = calls[0]
    assert "owner_user_id" in brand_sql
    assert brand_params == {"user_id": "owner"}
    kit_sql, kit_params = calls[1]
    assert kit_params == {"brand_ids": ["brand-1"]}


def test_brand_list_without_brands_skips_kit_query(monkeypatch):
    calls = []

    def fake_fetch_all(sql, params=None, **_kwargs):
        calls.append(sql)
        return []

    monkeypatch.setattr(db, "fetch_all", fake_fetch_all)

    assert brands.list_brands(User(id="owner", email="t@example.com", access_token="")) == []
    assert len(calls) == 1
