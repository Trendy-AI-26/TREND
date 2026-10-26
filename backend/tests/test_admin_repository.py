"""SQL built by app.repositories.admin, checked against a fake db layer."""

import json
from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest

from app import db
from app.repositories import admin as repo

USER_ID = "33333333-3333-4333-8333-333333333333"
ADMIN_ID = "11111111-1111-4111-8111-111111111111"
BRAND_ID = "44444444-4444-4444-8444-444444444444"
TREND_ID = "66666666-6666-4666-8666-666666666666"

AUDIT = {
    "admin_user_id": ADMIN_ID,
    "admin_email": "admin@example.com",
    "action": "user.test",
    "target_type": "user",
    "target_id": USER_ID,
    "details": {"amount": 5},
}


def _flat(sql: str) -> str:
    return " ".join(sql.split())


class FakeDb:
    """Records statements; answers fetches from ``(kind, needle) -> result`` rules."""

    def __init__(self, rules=None):
        self.rules = list(rules or [])
        self.calls: list[tuple[str, str, dict]] = []
        self.transactions = 0

    def _answer(self, kind, sql, params, default):
        self.calls.append((kind, _flat(sql), dict(params or {})))
        for rule_kind, needle, result in self.rules:
            if rule_kind == kind and needle in _flat(sql):
                return result(params) if callable(result) else result
        return default

    def fetch_one(self, sql, params=None, *, raw=False):
        return self._answer("one", sql, params, None)

    def fetch_all(self, sql, params=None, *, raw=False):
        return self._answer("all", sql, params, [])

    def execute(self, sql, params=None):
        return self._answer("exec", sql, params, 1)

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self

    def statements(self, needle):
        return [(kind, sql, params) for kind, sql, params in self.calls if needle in sql]


@pytest.fixture
def fake_db(monkeypatch):
    fake = FakeDb()
    for name in ("fetch_one", "fetch_all", "execute", "transaction"):
        monkeypatch.setattr(db, name, getattr(fake, name))
    return fake


def _audit_rows(fake):
    return fake.statements("INSERT INTO admin_audit_log")


# ------------------------------------------------------------------ helpers


def test_like_pattern_escapes_wildcards():
    assert repo.like_pattern("50%_off\\") == "%50\\%\\_off\\\\%"
    assert repo.like_pattern("ann") == "%ann%"


def test_needs_review_rule():
    sql = _flat(repo.NEEDS_REVIEW_SQL)

    assert "ir.status = 'processing'" in sql
    assert "ir.response_body ->> 'phase' IN ('outcome_unknown', 'cleanup_pending')" in sql
    assert "g.status IN ('pending', 'processing')" in sql
    assert "g.created_at < now() - interval '10 minutes'" in sql


def test_audit_row_falls_back_to_null_admin_id(fake_db):
    with db.transaction() as tx:
        repo._insert_audit(tx, AUDIT)

    (_, sql, params) = _audit_rows(fake_db)[0]
    assert "(SELECT id FROM users WHERE id = CAST(:admin_user_id AS uuid))" in sql
    assert params["target_id"] == USER_ID
    assert json.loads(params["details"]) == {"amount": 5}


# ------------------------------------------------------------------ lists


def test_list_users_filters_and_count_share_the_where_clause(fake_db):
    fake_db.rules = [
        ("all", "FROM users u", [{"id": USER_ID}]),
        ("one", "SELECT count(*) AS total", {"total": 7}),
    ]

    rows, total = repo.list_users(offset=24, limit=24, q="ann", verified=False, status="disabled")

    assert (rows, total) == ([{"id": USER_ID}], 7)
    assert fake_db.transactions == 1
    (_, list_sql, params), (_, count_sql, _) = fake_db.calls
    for sql in (list_sql, count_sql):
        assert "(u.email ILIKE :q OR p.full_name ILIKE :q)" in sql
        assert "u.email_verified_at IS NULL" in sql
        assert "u.disabled_at IS NOT NULL" in sql
    assert "ORDER BY u.created_at DESC, u.id DESC" in list_sql
    assert (params["q"], params["offset"], params["limit"]) == ("%ann%", 24, 24)


def test_list_users_without_filters_has_no_where(fake_db):
    repo.list_users(offset=0, limit=24)

    (_, list_sql, _), (_, count_sql, _) = fake_db.calls
    assert " WHERE " not in list_sql.split(") gc ON true")[1]
    assert " WHERE " not in count_sql


def test_user_select_counts_users_and_today_usage():
    sql = _flat(repo._USER_SELECT)

    assert "FROM users u" in sql
    assert "d.usage_date = (now() AT TIME ZONE 'utc')::date" in sql
    assert "count(*) FILTER (WHERE g.status = 'succeeded')" in sql


def test_list_generations_filters(fake_db):
    repo.list_generations(
        offset=0, limit=10, status="failed", provider="gemini", needs_review=True,
        q="acme", date_from=date(2026, 6, 1), date_to=date(2026, 6, 30),
    )

    (_, list_sql, params), (_, count_sql, _) = fake_db.calls
    for sql in (list_sql, count_sql):
        assert "g.status = CAST(:status AS generation_status_t)" in sql
        assert "g.provider = CAST(:provider AS provider_t)" in sql
        assert _flat(repo.NEEDS_REVIEW_SQL) in sql
        assert "(u.email ILIKE :q OR b.name ILIKE :q)" in sql
        assert "(CAST(:date_to AS date) + 1)::timestamp AT TIME ZONE 'utc'" in sql
    assert "ORDER BY g.created_at DESC, g.id DESC" in list_sql
    assert (params["date_from"], params["date_to"]) == ("2026-06-01", "2026-06-30")


def test_list_generations_can_exclude_needs_review(fake_db):
    repo.list_generations(offset=0, limit=10, needs_review=False)

    assert f"NOT {_flat(repo.NEEDS_REVIEW_SQL)}" in fake_db.calls[0][1]


def test_list_brands_filters(fake_db):
    repo.list_brands(offset=0, limit=24, q="acme", kit_status="not_started")

    (_, list_sql, params), (_, count_sql, _) = fake_db.calls
    for sql in (list_sql, count_sql):
        assert "(b.name ILIKE :q OR u.email ILIKE :q)" in sql
        assert "COALESCE(bk.status::text, 'not_started') = :kit_status" in sql
    assert "COALESCE(cardinality(bk.colors), 0) AS colors_count" in list_sql
    assert "(b.logo_path IS NOT NULL) AS has_logo" in list_sql
    assert params["kit_status"] == "not_started"


def test_daily_outcomes_series(fake_db):
    repo.get_daily_outcomes(30)

    (_, sql, params) = fake_db.calls[0]
    assert params == {"days": 30}
    assert "generate_series(" in sql and "ORDER BY day.d" in sql


def test_audit_log_is_newest_first(fake_db):
    fake_db.rules = [("one", "count(*)", {"total": 3})]

    rows, total = repo.list_audit_log(offset=0, limit=5)

    assert total == 3
    assert "ORDER BY created_at DESC, id DESC" in fake_db.calls[0][1]


# ------------------------------------------------------------------ user actions


def test_grant_generations_is_one_transaction_with_its_audit(fake_db):
    result = {"generation_limit": 47, "credit_balance": 47}
    fake_db.rules = [
        ("one", "SELECT id FROM users WHERE id", {"id": USER_ID}),
        ("one", "admin_grant_generations(", {"result": result}),
    ]

    returned = repo.grant_generations(
        USER_ID,
        generations=5,
        credits=5,
        idempotency_key="admin-grant:abc",
        metadata={"note": "promo"},
        audit=AUDIT,
    )

    assert returned == result
    assert fake_db.transactions == 1
    kinds = [sql.split()[0] for _, sql, _ in fake_db.calls]
    assert kinds == ["SELECT", "SELECT", "INSERT"]
    (_, _, params) = fake_db.statements("admin_grant_generations(")[0]
    assert (params["user_id"], params["generations"], params["credits"]) == (USER_ID, 5, 5)
    assert params["idempotency_key"] == "admin-grant:abc"
    assert json.loads(params["metadata"]) == {"note": "promo"}
    assert len(_audit_rows(fake_db)) == 1


def test_grant_generations_unknown_user_writes_nothing(fake_db):
    assert repo.grant_generations(
        USER_ID, generations=1, credits=1, idempotency_key="k", metadata={}, audit=AUDIT
    ) is None
    assert fake_db.statements("admin_grant_generations(") == []
    assert _audit_rows(fake_db) == []


def test_reset_daily_usage_only_touches_consumed(fake_db):
    fake_db.rules = [
        ("one", "SELECT id FROM users WHERE id", {"id": USER_ID}),
        ("one", "FROM generation_daily_usage", {"usage_date": "2026-06-20", "consumed": 2, "reserved": 1}),
    ]

    result = repo.reset_daily_usage(USER_ID, AUDIT)

    assert result == {"usage_date": "2026-06-20", "previous_consumed": 2}
    (_, update_sql, params) = fake_db.statements("UPDATE generation_daily_usage")[0]
    set_clause = update_sql.split(" SET ")[1].split(" WHERE ")[0]
    assert set_clause == "consumed = 0, updated_at = now()"
    assert "reserved" not in set_clause
    assert params["usage_date"] == "2026-06-20"
    (_, _, audit_params) = _audit_rows(fake_db)[0]
    assert json.loads(audit_params["details"])["previous_consumed"] == 2


def test_reset_daily_usage_without_a_row_today_is_a_noop_but_audited(fake_db):
    fake_db.rules = [("one", "SELECT id FROM users WHERE id", {"id": USER_ID})]

    assert repo.reset_daily_usage(USER_ID, AUDIT) == {"usage_date": None, "previous_consumed": 0}
    assert fake_db.statements("UPDATE generation_daily_usage") == []
    assert len(_audit_rows(fake_db)) == 1


def test_extend_trial_extends_from_the_later_of_now_and_the_current_end(fake_db):
    fake_db.rules = [
        ("one", "SELECT id FROM users WHERE id", {"id": USER_ID}),
        ("one", "SELECT trial_ends_at FROM profiles", {"trial_ends_at": "2026-06-15T09:00:00+00:00"}),
        ("one", "INSERT INTO profiles", {"trial_ends_at": "2026-07-15T09:00:00+00:00"}),
    ]

    row = repo.extend_trial(USER_ID, 30, AUDIT)

    assert row == {"trial_ends_at": "2026-07-15T09:00:00+00:00"}
    (_, sql, params) = fake_db.statements("INSERT INTO profiles")[0]
    assert "GREATEST(profiles.trial_ends_at, now()) + make_interval(days => CAST(:days AS integer))" in sql
    assert params["days"] == 30
    details = json.loads(_audit_rows(fake_db)[0][2]["details"])
    assert details["previous_trial_ends_at"] == "2026-06-15T09:00:00+00:00"


@pytest.mark.parametrize(("disabled", "expected"), [(True, "COALESCE(disabled_at, now())"), (False, "NULL")])
def test_set_user_disabled(fake_db, disabled, expected):
    fake_db.rules = [("one", "SELECT disabled_at FROM users", {"disabled_at": None})]

    repo.set_user_disabled(USER_ID, disabled, AUDIT)

    (_, sql, _) = fake_db.statements("UPDATE users SET disabled_at")[0]
    assert f"SET disabled_at = {expected} " in sql
    assert json.loads(_audit_rows(fake_db)[0][2]["details"])["was_disabled"] is False


@pytest.mark.parametrize(
    "action",
    [
        lambda: repo.verify_user_email(USER_ID, AUDIT),
        lambda: repo.set_user_disabled(USER_ID, True, AUDIT),
        lambda: repo.extend_trial(USER_ID, 3, AUDIT),
        lambda: repo.reset_daily_usage(USER_ID, AUDIT),
        lambda: repo.delete_user(USER_ID, AUDIT),
    ],
)
def test_actions_on_unknown_users_return_none_and_do_not_audit(fake_db, action):
    assert action() is None
    assert _audit_rows(fake_db) == []
    assert fake_db.statements("DELETE FROM users") == []


def test_delete_user_collects_files_then_deletes_and_audits(fake_db):
    logo = f"brands/{BRAND_ID}/logo.png"
    image = f"brands/{BRAND_ID}/generations/{USER_ID}.png"
    asset = f"brands/{BRAND_ID}/product-assets/{USER_ID}.png"
    fake_db.rules = [
        ("one", "SELECT u.id, u.email, p.avatar_path",
         {"id": USER_ID, "email": "u@example.com", "avatar_path": f"avatars/{USER_ID}/avatar.png"}),
        ("all", "SELECT logo_path AS path", [{"path": logo}]),
        ("all", "SELECT g.image_path AS path", [{"path": image}]),
        ("all", "SELECT pa.storage_path AS path", [{"path": asset}, {"path": asset}]),
        ("one", "count(*) AS total FROM brands", {"total": 1}),
    ]

    result = repo.delete_user(USER_ID, AUDIT)

    assert result == {
        "email": "u@example.com",
        "brand_files": [logo, image],
        "product_asset_files": [asset],
        "avatar_files": [f"avatars/{USER_ID}/avatar.png"],
    }
    assert fake_db.transactions == 1
    order = [sql for _, sql, _ in fake_db.calls]
    delete_at = next(i for i, sql in enumerate(order) if sql.startswith("DELETE FROM users"))
    audit_at = next(i for i, sql in enumerate(order) if sql.startswith("INSERT INTO admin_audit_log"))
    assert all("path" in sql or "count" in sql or "avatar_path" in sql for sql in order[:delete_at])
    assert delete_at < audit_at
    details = json.loads(fake_db.calls[audit_at][2]["details"])
    assert (details["email"], details["brands"]) == ("u@example.com", 1)


# ------------------------------------------------------------------ trends


def test_create_trend_serializes_json_arrays_and_audits(fake_db):
    row = {"id": TREND_ID, "slug": "neon", "name": "Neon"}
    fake_db.rules = [("one", "INSERT INTO trends", row)]
    values = {
        "name": "Neon", "slug": "neon", "description": None, "category": None,
        "industry": ["food"], "region": [], "platform": [], "audience": [],
        "visual_style": [], "content_patterns": [], "keywords": ["a", "b"],
        "avoid_patterns": [], "popularity_score": 1, "growth_score": 2,
        "relevance_score": 3, "status": "active", "source": None, "observed_at": None,
        "expires_at": datetime(2026, 12, 31, tzinfo=timezone.utc),
    }

    assert repo.create_trend(values, {**AUDIT, "target_type": "trend", "target_id": None}) == row

    (_, sql, params) = fake_db.statements("INSERT INTO trends")[0]
    assert "CAST(:keywords AS jsonb)" in sql and "CAST(:expires_at AS timestamptz)" in sql
    assert json.loads(params["keywords"]) == ["a", "b"]
    assert params["expires_at"] == "2026-12-31T00:00:00+00:00"
    (_, _, audit) = _audit_rows(fake_db)[0]
    assert (audit["target_type"], audit["target_id"]) == ("trend", TREND_ID)


def test_update_trend_sets_only_the_changed_columns(fake_db):
    fake_db.rules = [("one", "UPDATE trends", {"id": TREND_ID, "slug": "neon", "name": "Neon"})]

    repo.update_trend(TREND_ID, {"status": "inactive", "keywords": ["x"]}, AUDIT)

    (_, sql, params) = fake_db.statements("UPDATE trends")[0]
    assert "SET status = :status, keywords = CAST(:keywords AS jsonb), updated_at = now()" in sql
    assert json.loads(_audit_rows(fake_db)[0][2]["details"])["fields"] == ["keywords", "status"]


def test_update_trend_without_changes_just_reads(fake_db):
    fake_db.rules = [("one", "FROM trends WHERE id", {"id": TREND_ID})]

    assert repo.update_trend(TREND_ID, {}, AUDIT) == {"id": TREND_ID}
    assert fake_db.statements("UPDATE trends") == [] and _audit_rows(fake_db) == []


def test_delete_trend(fake_db):
    fake_db.rules = [
        ("one", "count(*) AS total FROM generations", {"total": 2}),
        ("one", "DELETE FROM trends", {"id": TREND_ID, "slug": "neon", "name": "Neon"}),
    ]

    assert repo.delete_trend(TREND_ID, AUDIT)["id"] == TREND_ID
    details = json.loads(_audit_rows(fake_db)[0][2]["details"])
    assert details["generations_unlinked"] == 2


def test_delete_unknown_trend_is_none(fake_db):
    assert repo.delete_trend(TREND_ID, AUDIT) is None
    assert _audit_rows(fake_db) == []
