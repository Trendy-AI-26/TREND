from types import SimpleNamespace

from app.core.auth import User
from app.routers import brands


def test_brand_list_batches_summary_and_keeps_owner_filter(monkeypatch):
    calls = []
    rows = {
        "brands": [{
            "id": "brand-1", "name": "Brand", "created_at": "2026-10-07T00:00:00Z",
        }],
        "brand_kits": [{
            "brand_id": "brand-1", "status": "complete", "colors": ["#123456"],
            "industry": "Food", "tagline": "Fresh",
        }],
    }

    class Query:
        def __init__(self, table):
            self.table_name = table

        def select(self, columns):
            calls.append((self.table_name, "select", columns))
            return self

        def eq(self, column, value):
            calls.append((self.table_name, "eq", column, value))
            return self

        def in_(self, column, values):
            calls.append((self.table_name, "in", column, values))
            return self

        def order(self, *args, **kwargs):
            return self

        def execute(self):
            calls.append((self.table_name, "execute"))
            return SimpleNamespace(data=rows[self.table_name])

    monkeypatch.setattr(brands, "get_service_client", lambda: SimpleNamespace(table=Query))
    result = brands.list_brands(User(id="owner", email="test@example.com", access_token=""))
    assert result[0].colors == ["#123456"]
    assert result[0].industry == "Food"
    assert result[0].tagline == "Fresh"
    assert ("brands", "eq", "owner_user_id", "owner") in calls
    assert ("brand_kits", "in", "brand_id", ["brand-1"]) in calls
    assert sum(call[-1] == "execute" for call in calls) == 2
