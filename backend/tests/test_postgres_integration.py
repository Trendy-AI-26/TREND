"""Runs the real SQL against a real PostgreSQL. Skipped unless TEST_DATABASE_URL is set.

    $env:TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:5432/trendy_test"

WARNING: the target database's `public` schema is DROPPED and recreated. Use a
throwaway database.
"""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone
from threading import Barrier

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set (needs a throwaway PostgreSQL)"
)


@pytest.fixture(scope="module")
def pg():
    import psycopg

    from app import db
    from app.config import settings
    from app.db import migrate
    from postgres_test_safety import prepare_disposable_test_schema

    original = settings.DATABASE_URL
    dsn = prepare_disposable_test_schema(
        TEST_DATABASE_URL,
        confirmation=os.environ.get("ALLOW_DESTRUCTIVE_TEST_DB"),
        normal_database_url=original,
        database_dsn=migrate.database_dsn,
        connect=psycopg.connect,
    )

    settings.DATABASE_URL = TEST_DATABASE_URL
    db.reset_engine()
    first = migrate.run_migrations(dsn)
    second = migrate.run_migrations(dsn)
    yield {"first": first, "second": second, "dsn": dsn}

    db.reset_engine()
    settings.DATABASE_URL = original


def _new_user(email=None):
    from app.repositories import users

    email = email or f"{uuid.uuid4().hex[:10]}@example.com"
    user = users.create_user(email, "$2b$12$hash", "Test Person")
    return str(user["id"])


def _new_brand(user_id, name=None):
    from app.services import quota

    return quota.create_brand_if_allowed(user_id=user_id, name=name or f"Brand {uuid.uuid4().hex[:6]}")


def _new_generation(brand_id, user_id, **overrides):
    from app.repositories import generations as gens

    values = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "brand_id": brand_id,
        "prompt": "A prompt that is long enough",
        "brief": {"core_idea": "x"},
        "language": "en",
        "provider": "openai",
        "model": "gpt-image-2",
        "idempotency_key": f"key-{uuid.uuid4()}",
        "platform_preset": "instagram_reel_cover",
        "width": 1080,
        "height": 1920,
        "logo_mode": "none",
        "product_asset_id": None,
        "trend_id": None,
        "trend_snapshot": None,
        "trend_applied": False,
    }
    values.update(overrides)
    return gens.insert_generation(values)


def test_baseline_applies_once_then_is_a_noop(pg):
    assert pg["first"] == [
        "0001_baseline.sql",
        "0002_kit_complete_without_tone.sql",
        "0003_brand_kit_four_colors.sql",
    ]
    assert pg["second"] == []


def test_plans_seed_has_final_values(pg):
    from app import db

    row = db.fetch_one("SELECT * FROM plans WHERE code = 'beta'")

    assert (row["image_credits"], row["max_active_brands"], row["lifetime_image_limit"]) == (42, 3, 42)


def test_signup_creates_profile_via_trigger_and_email_is_case_insensitive_unique(pg):
    from app import db
    from app.repositories import users

    user = users.create_user("Mixed.Case@Example.com", "$2b$12$hash", "Test Person")
    profile = db.fetch_one("SELECT * FROM profiles WHERE user_id = :u", {"u": user["id"]})

    assert profile["full_name"] == "Test Person"
    assert users.get_user_by_email("mixed.case@example.COM")["id"] == user["id"]
    with pytest.raises(db.IntegrityError) as error:
        users.create_user("MIXED.CASE@example.com", "$2b$12$hash", None)
    assert db.is_unique_violation(error.value, "uq_users_email_ci")


def test_auth_code_lifecycle(pg):
    from app.repositories import users

    user_id = _new_user()
    now = datetime.now(timezone.utc)
    assert users.issue_code_if_allowed(
        user_id,
        "verify_email",
        "hash-1",
        now + timedelta(minutes=15),
        now,
        60,
    ) == "issued"
    first = users.latest_code(user_id, "verify_email")
    assert users.issue_code_if_allowed(
        user_id,
        "verify_email",
        "hash-2",
        now + timedelta(minutes=16, seconds=1),
        now + timedelta(seconds=61),
        60,
    ) == "issued"
    latest = users.latest_code(user_id, "verify_email")

    assert latest["code_hash"] == "hash-2"
    assert users.increment_attempts(first["id"]) is None  # superseded code is consumed
    assert users.increment_attempts(latest["id"]) == 1
    assert users.increment_attempts(latest["id"]) == 2
    assert users.consume_code(latest["id"], now) is True
    assert users.consume_code(latest["id"], now) is False
    assert users.latest_code(user_id, "reset_password") is None


def test_verification_code_issuance_is_serialized_per_user(pg):
    from app import db
    from app.repositories import users

    user_id = _new_user()
    now = datetime.now(UTC)
    barrier = Barrier(2)

    def issue(code_hash):
        barrier.wait()
        return users.issue_code_if_allowed(
            user_id,
            "verify_email",
            code_hash,
            now + timedelta(minutes=15),
            now,
            60,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(issue, ("hash-a", "hash-b")))

    assert sorted(results) == ["cooldown", "issued"]
    rows = db.fetch_all(
        """
        SELECT code_hash FROM auth_codes
        WHERE user_id = CAST(:user_id AS uuid) AND purpose = 'verify_email'
          AND consumed_at IS NULL
        """,
        {"user_id": user_id},
    )
    assert len(rows) == 1
    assert rows[0]["code_hash"] in {"hash-a", "hash-b"}


def test_verification_and_reissue_race_has_one_safe_outcome(pg):
    from app.repositories import users

    user_id = _new_user()
    issued_at = datetime.now(UTC)
    assert users.issue_code_if_allowed(
        user_id,
        "verify_email",
        "old-hash",
        issued_at + timedelta(minutes=15),
        issued_at,
        60,
    ) == "issued"
    old = users.latest_code(user_id, "verify_email")
    race_time = issued_at + timedelta(seconds=61)
    barrier = Barrier(2)

    def verify():
        barrier.wait()
        return users.consume_verification_code_and_mark_verified(
            user_id, old["id"], race_time
        )

    def reissue():
        barrier.wait()
        return users.issue_code_if_allowed(
            user_id,
            "verify_email",
            "new-hash",
            race_time + timedelta(minutes=15),
            race_time,
            60,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        verify_result = pool.submit(verify)
        issue_result = pool.submit(reissue)
        verified, issuance = verify_result.result(), issue_result.result()

    user = users.get_user_by_id(user_id)
    latest = users.latest_code(user_id, "verify_email")
    if verified:
        assert issuance == "ineligible"
        assert user["email_verified_at"] is not None
        assert latest["code_hash"] == "old-hash"
        assert latest["consumed_at"] is not None
    else:
        assert issuance == "issued"
        assert user["email_verified_at"] is None
        assert latest["code_hash"] == "new-hash"
        assert latest["consumed_at"] is None


def test_repeated_signup_keeps_original_credentials_in_postgres(pg):
    from app.core.security import verify_password
    from app.repositories import users
    from app.services import auth_service

    email = f"repeat-{uuid.uuid4().hex[:10]}@example.com"
    auth_service.signup(email, "original password", "Original Name")
    auth_service.signup(email, "attacker password", "Attacker Name")

    user = users.get_user_by_email(email)
    assert verify_password("original password", user["password_hash"])
    assert not verify_password("attacker password", user["password_hash"])
    assert user["full_name"] == "Original Name"


def test_concurrent_first_signups_keep_one_winners_credentials(pg):
    from app.core.security import verify_password
    from app.repositories import users
    from app.services import auth_service

    email = f"concurrent-{uuid.uuid4().hex[:10]}@example.com"
    barrier = Barrier(2)

    def signup(password, name):
        barrier.wait()
        return auth_service.signup(email, password, name)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(signup, "first password", "First Name")
        second = pool.submit(signup, "second password", "Second Name")
        results = (first.result(), second.result())

    user = users.get_user_by_email(email)
    first_won = verify_password("first password", user["password_hash"])
    second_won = verify_password("second password", user["password_hash"])
    assert first_won != second_won
    assert user["full_name"] == ("First Name" if first_won else "Second Name")
    assert sum(result is not None for result in results) == 1


def test_signup_without_verification_still_rejects_existing_user_in_postgres(pg):
    from app.core.security import verify_password
    from app.repositories import users
    from app.services import auth_service

    email = f"no-verify-{uuid.uuid4().hex[:10]}@example.com"
    auth_service.signup_without_verification(email, "original password", "Original Name")

    with pytest.raises(auth_service.AuthError) as error:
        auth_service.signup_without_verification(
            email, "attacker password", "Attacker Name"
        )

    assert error.value.status_code == 409
    assert error.value.code == "EMAIL_ALREADY_REGISTERED"
    user = users.get_user_by_email(email)
    assert verify_password("original password", user["password_hash"])
    assert not verify_password("attacker password", user["password_hash"])
    assert user["full_name"] == "Original Name"


def test_brand_limit_duplicates_and_ownership(pg):
    from app import db
    from app.repositories import brands as brand_repo
    from app.services import quota

    owner, stranger = _new_user(), _new_user()
    first = _new_brand(owner, "  Alpha  ")
    assert first["name"] == "Alpha"
    _new_brand(owner, "Beta")
    with pytest.raises(quota.QuotaError) as dup:
        _new_brand(owner, "ALPHA")
    assert dup.value.code == "DUPLICATE_BRAND_NAME"
    _new_brand(owner, "Gamma")
    with pytest.raises(quota.QuotaError) as limit:
        _new_brand(owner, "Delta")
    assert limit.value.code == "BRAND_LIMIT_REACHED"

    assert brand_repo.get_owned_brand(first["id"], owner)["name"] == "Alpha"
    assert brand_repo.get_owned_brand(first["id"], stranger) is None
    assert len(brand_repo.list_brands(owner)) == 3

    with pytest.raises(db.IntegrityError) as error:
        brand_repo.rename_brand(first["id"], "beta")
    assert db.is_unique_violation(error.value, "uq_brands_owner_name_ci")
    assert brand_repo.rename_brand(first["id"], "Omega")["name"] == "Omega"


def test_kit_upsert_and_list_summaries(pg):
    from app.repositories import brands as brand_repo

    owner = _new_user()
    brand = _new_brand(owner)
    payload = {
        "brand_id": brand["id"],
        "product_asset_id": None,
        "tagline": "Fresh",
        "tone": "friendly",
        "industry": "Food",
        "audience": "Everyone nearby",
        "colors": ["#123456", "#abcdef"],
        "avoid_words": None,
        "summary": "s",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    row = brand_repo.upsert_kit(payload)
    assert row["colors"] == ["#123456", "#abcdef"] and row["status"] == "complete"

    row = brand_repo.upsert_kit({**payload, "status": "in_progress", "completed_at": None, "colors": []})
    assert row["status"] == "in_progress" and row["colors"] == []

    summaries = brand_repo.kit_summaries([brand["id"], str(uuid.uuid4())])
    assert [s["brand_id"] for s in summaries] == [brand["id"]]
    assert brand_repo.get_kit_status(brand["id"]) == "in_progress"


@pytest.mark.parametrize("count", [1, 3, 4])
def test_kit_palette_round_trips(pg, count):
    from app.repositories import brands as brand_repo

    brand = _new_brand(_new_user())
    colors = [f"#{index:06X}" for index in range(count)]
    payload = {
        "brand_id": brand["id"],
        "product_asset_id": None,
        "tagline": None,
        "tone": None,
        "industry": "Retail",
        "audience": "Local customers",
        "colors": colors,
        "avoid_words": None,
        "summary": "Palette test",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    assert brand_repo.upsert_kit(payload)["colors"] == colors
    assert brand_repo.get_kit(brand["id"])["colors"] == colors
    assert brand_repo.kit_summaries([brand["id"]])[0]["colors"] == colors


def test_history_cursor_pagination_has_no_gaps_or_duplicates(pg):
    from app.repositories import generations as gens

    owner = _new_user()
    brand = _new_brand(owner)
    ids = []
    for index in range(5):
        row = _new_generation(brand["id"], owner)
        ids.append(row["id"])
        now = datetime.now(timezone.utc).isoformat()
        if index % 2 == 0:
            gens.mark_succeeded(
                row["id"], f"brands/{brand['id']}/generations/{row['id']}.png", "req", now
            )
        else:
            gens.mark_failed(row["id"], "ERR", "boom", now)
    _new_generation(brand["id"], owner)  # pending: never listed

    seen, cursor = [], None
    while True:
        page = gens.list_history(brand["id"], provider=None, status=None, cursor=cursor, limit=3)
        seen.extend(r["id"] for r in page[:2])
        if len(page) <= 2:
            break
        cursor = (page[1]["created_at"], page[1]["id"])

    assert sorted(seen) == sorted(ids) and len(seen) == len(set(seen)) == 5
    assert gens.count_succeeded(brand["id"]) == 3
    assert {r["status"] for r in gens.list_history(
        brand["id"], provider="openai", status="failed", cursor=None, limit=10)} == {"failed"}


def test_idempotency_record_unique_per_user_scope_key(pg):
    from app import db
    from app.repositories import generations as gens

    owner = _new_user()
    record = gens.create_idempotency(owner, "image_generation", "k" * 16, "hash")
    assert gens.get_idempotency(owner, "image_generation", "k" * 16)["id"] == record["id"]
    with pytest.raises(db.IntegrityError):
        gens.create_idempotency(owner, "image_generation", "k" * 16, "hash")

    brand = _new_brand(owner)
    generation = _new_generation(brand["id"], owner)
    gens.link_idempotency(record["id"], generation["id"])
    gens.finish_idempotency(record["id"], "succeeded", 200, datetime.now(timezone.utc).isoformat())
    done = gens.get_idempotency(owner, "image_generation", "k" * 16)
    assert (done["status"], done["generation_id"], done["response_status"]) == ("succeeded", generation["id"], 200)


def test_quota_slots_daily_limit_and_summary(pg):
    from app.services import quota

    owner = _new_user()
    brand = _new_brand(owner)
    generations = [_new_generation(brand["id"], owner) for _ in range(4)]

    for generation in generations[:3]:
        quota.reserve_generation_slot(user_id=owner, generation_id=generation["id"])
    with pytest.raises(quota.QuotaError) as error:
        quota.reserve_generation_slot(user_id=owner, generation_id=generations[3]["id"])
    assert error.value.code == "DAILY_GENERATION_LIMIT_REACHED"

    quota.release_generation_slot(user_id=owner, generation_id=generations[0]["id"])
    quota.release_generation_slot(user_id=owner, generation_id=generations[0]["id"])  # idempotent
    quota.commit_generation_slot(user_id=owner, generation_id=generations[1]["id"])
    quota.commit_generation_slot(user_id=owner, generation_id=generations[1]["id"])  # idempotent

    summary = quota.get_quota_summary(user_id=owner)
    assert summary.generation_limit == 42
    assert (summary.generation_consumed, summary.generation_reserved) == (1, 1)
    assert summary.daily_generation_remaining == 1
    assert summary.trial_active is True and summary.trial_ends_at is not None
    assert summary.active_brands == 1

    with pytest.raises(quota.QuotaError) as exists:
        quota.reserve_generation_slot(user_id=owner, generation_id=generations[2]["id"])
    assert exists.value.code == "GENERATION_QUOTA_RESERVATION_EXISTS"


def test_expired_trial_blocks_generation(pg):
    from app import db
    from app.services import quota

    owner = _new_user()
    brand = _new_brand(owner)
    generation = _new_generation(brand["id"], owner)
    db.execute(
        "UPDATE profiles SET trial_ends_at = now() - interval '1 minute' WHERE user_id = CAST(:u AS uuid)",
        {"u": owner},
    )

    with pytest.raises(quota.QuotaError) as error:
        quota.reserve_generation_slot(user_id=owner, generation_id=generation["id"])
    assert error.value.code == "TRIAL_EXPIRED"


def test_credits_reserve_commit_release(pg):
    from app import db
    from app.services import credits

    owner = _new_user()
    brand = _new_brand(owner)
    first, second = _new_generation(brand["id"], owner), _new_generation(brand["id"], owner)

    reservation = credits.reserve_credits(
        user_id=owner, generation_id=first["id"], idempotency_key="generation:1:reserve"
    )
    assert credits.get_available_credits(owner) == 41
    with pytest.raises(credits.CreditsError) as reused:
        credits.reserve_credits(
            user_id=owner, generation_id=first["id"], idempotency_key="generation:1:reserve"
        )
    assert reused.value.code == "IDEMPOTENCY_KEY_REUSED"

    credits.commit_credits(reservation)
    credits.commit_credits(reservation)  # retry is a no-op
    assert credits.get_available_credits(owner) == 41

    other = credits.reserve_credits(
        user_id=owner, generation_id=second["id"], idempotency_key="generation:2:reserve"
    )
    credits.release_credits(other)
    credits.release_credits(other)
    assert credits.get_available_credits(owner) == 41
    with pytest.raises(credits.CreditsError) as committed:
        credits.release_credits(reservation)
    assert committed.value.code == "CREDIT_ALREADY_COMMITTED"

    with pytest.raises(credits.CreditsError) as insufficient:
        credits.reserve_credits(user_id=owner, generation_id=second["id"], amount=1000)
    assert insufficient.value.code == "INSUFFICIENT_CREDITS"
    balance = db.fetch_one("SELECT balance, reserved FROM credit_accounts WHERE user_id = CAST(:u AS uuid)", {"u": owner})
    assert (balance["balance"], balance["reserved"]) == (41, 0)


def test_rate_limit_bucket(pg):
    from app.services import rate_limit

    owner = _new_user()
    rate_limit.check_generation_rate_limit(user_id=owner, limit=2, window_seconds=3600)
    rate_limit.check_generation_rate_limit(user_id=owner, limit=2, window_seconds=3600)
    with pytest.raises(rate_limit.RateLimitExceeded):
        rate_limit.check_generation_rate_limit(user_id=owner, limit=2, window_seconds=3600)


def test_generation_lock_before_the_generation_row_exists(pg):
    from app import db
    from app.services import generation_lock as lock

    owner = _new_user()
    first, second = uuid.uuid4(), uuid.uuid4()

    lock.acquire_generation_lock(user_id=owner, generation_id=first)
    with pytest.raises(lock.GenerationLockError):
        lock.acquire_generation_lock(user_id=owner, generation_id=second)
    lock.release_generation_lock(user_id=owner, generation_id=second)  # wrong id: keeps the lock
    with pytest.raises(lock.GenerationLockError):
        lock.acquire_generation_lock(user_id=owner, generation_id=second)

    lock.release_generation_lock(user_id=owner, generation_id=first)
    lock.acquire_generation_lock(user_id=owner, generation_id=second)

    db.execute(
        "UPDATE generation_locks SET expires_at = now() - interval '1 second' WHERE user_id = CAST(:u AS uuid)",
        {"u": owner},
    )
    lock.acquire_generation_lock(user_id=owner, generation_id=first)  # expired lock is replaced


def test_usage_events(pg):
    from app import db
    from app.services import usage

    owner = _new_user()
    brand = _new_brand(owner)
    generation = _new_generation(brand["id"], owner)
    timer = usage.UsageTimer(
        user_id=owner, generation_id=generation["id"], feature="image_generation",
        provider="openai", model="gpt-image-2", credits=1,
    )
    timer.start()
    timer.finish(status="succeeded", metadata={"a": 1}, provider_request_id="req-1")

    row = db.fetch_one("SELECT * FROM usage_events WHERE id = CAST(:i AS uuid)", {"i": timer.usage_id})
    assert (row["status"], row["metadata"], row["provider_request_id"]) == ("succeeded", {"a": 1}, "req-1")


def test_provider_keys_are_encrypted_and_one_active(pg):
    from app import db
    from app.core.vault import decrypt_secret, encrypt_secret
    from app.repositories import provider_keys as keys

    owner = _new_user()
    brand = _new_brand(owner)

    def add(secret, active=True):
        return keys.insert_key(
            {
                "brand_id": brand["id"], "provider": "openai",
                "encrypted_key": encrypt_secret(secret), "label": None, "key_hint": secret[-4:],
                "is_active": active, "is_valid": True,
                "last_validated_at": datetime.now(timezone.utc).isoformat(),
                "last_validation_error": None,
            },
            deactivate_existing=active,
        )

    one = add("sk-first-1111")
    two = add("sk-second-2222")
    listed = {k["id"]: k for k in keys.list_keys(brand["id"])}
    assert listed[one["id"]]["is_active"] is False and listed[two["id"]]["is_active"] is True
    assert "encrypted_key" not in listed[one["id"]]
    assert decrypt_secret(keys.get_key(brand["id"], two["id"])["encrypted_key"]) == "sk-second-2222"

    with pytest.raises(db.IntegrityError) as conflict:
        add("sk-third-3333", active=False) and keys.insert_key(
            {**{"brand_id": brand["id"], "provider": "openai", "encrypted_key": "x", "label": None,
                "key_hint": "3333", "is_active": True, "is_valid": None,
                "last_validated_at": datetime.now(timezone.utc).isoformat(),
                "last_validation_error": None}},
            deactivate_existing=False,
        )
    assert db.is_unique_violation(conflict.value, "uq_provider_keys_one_active")

    swapped = keys.activate_key(brand["id"], one["id"], "openai")
    assert swapped["is_active"] is True
    assert sum(k["is_active"] for k in keys.list_keys(brand["id"])) == 1
    keys.update_validation(one["id"], validated_at=datetime.now(timezone.utc).isoformat(), error="bad", is_valid=None)
    assert keys.get_key(brand["id"], one["id"])["is_valid"] is True  # None keeps the verdict
    keys.delete_key(one["id"])
    assert keys.get_key(brand["id"], one["id"]) is None


def test_product_assets_ownership_and_set_null_on_delete(pg):
    from app import db
    from app.repositories import brands as brand_repo
    from app.repositories import product_assets as assets

    owner, stranger = _new_user(), _new_user()
    brand = _new_brand(owner)
    asset_id = str(uuid.uuid4())
    saved = assets.insert_asset(
        {
            "id": asset_id, "brand_id": brand["id"], "owner_user_id": owner,
            "storage_path": f"brands/{brand['id']}/product-assets/{asset_id}.png",
            "content_type": "image/png", "file_size_bytes": 10, "width": 5, "height": 5,
        }
    )
    assert assets.get_owned_asset(asset_id, brand["id"], owner)["storage_path"] == saved["storage_path"]
    assert assets.get_owned_asset(asset_id, brand["id"], stranger) is None
    assert brand_repo.product_asset_exists(asset_id, brand["id"], owner) is True
    assert brand_repo.product_asset_exists(asset_id, brand["id"], stranger) is False

    generation = _new_generation(brand["id"], owner, product_asset_id=asset_id)
    assets.delete_asset(asset_id, brand["id"], stranger)  # not the owner: nothing happens
    assert assets.get_owned_asset(asset_id, brand["id"], owner) is not None
    assets.delete_asset(asset_id, brand["id"], owner)
    row = db.fetch_one("SELECT product_asset_id FROM generations WHERE id = CAST(:i AS uuid)", {"i": generation["id"]})
    assert row["product_asset_id"] is None


def test_profile_updates(pg):
    from app.repositories import profiles

    owner = _new_user()
    updated = profiles.update_profile(owner, {"full_name": "New Name", "avatar_url": "https://x.test/a.png"})
    assert (updated["full_name"], updated["avatar_url"]) == ("New Name", "https://x.test/a.png")
    path = f"avatars/{owner}/avatar.png"
    row = profiles.set_avatar_path(owner, path)
    assert row["avatar_path"] == path and row["avatar_url"] is None
    assert profiles.get_avatar_path(owner)["avatar_path"] == path
    assert profiles.set_avatar_path(owner, None)["avatar_path"] is None
    assert profiles.get_profile(str(uuid.uuid4())) is None


def test_trends_queries(pg):
    from app import db
    from app.services import trend_service

    trend_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO trends (id, name, slug, platform) VALUES (CAST(:i AS uuid), 'T', :s, CAST(:p AS jsonb))",
        {"i": trend_id, "s": f"t-{trend_id}", "p": '["instagram"]'},
    )
    assert trend_service.get_active_trend_or_404(uuid.UUID(trend_id))["platform"] == ["instagram"]
    assert any(t["id"] == trend_id for t in db.fetch_all("SELECT * FROM trends WHERE status = 'active' LIMIT 100"))


def test_admin_views(pg):
    from app.repositories import admin

    owner = _new_user()
    _new_brand(owner, "Admin Visible")

    stats = admin.get_stats()
    assert stats["total_accounts"] >= 1 and stats["total_brands"] >= 1
    rows, total = admin.list_brands(0, 2)
    assert total >= len(rows) >= 1
    assert {"id", "name", "owner_user_id", "owner_full_name", "kit_status", "generation_count",
            "has_active_key", "created_at"} <= set(rows[0])


def test_deleting_a_user_cascades(pg):
    from app import db

    owner = _new_user()
    brand = _new_brand(owner)
    _new_generation(brand["id"], owner)

    db.execute("DELETE FROM users WHERE id = CAST(:u AS uuid)", {"u": owner})

    for table, column in (("profiles", "user_id"), ("brands", "owner_user_id"), ("credit_accounts", "user_id")):
        assert db.fetch_one(f"SELECT 1 AS x FROM {table} WHERE {column} = CAST(:u AS uuid)", {"u": owner}) is None
    assert db.fetch_one("SELECT 1 AS x FROM generations WHERE brand_id = CAST(:b AS uuid)", {"b": brand["id"]}) is None
