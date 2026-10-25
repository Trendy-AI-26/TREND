"""Slow database reads must not block unrelated requests on the event loop."""

import asyncio
import threading

import httpx
from fastapi import FastAPI

from app.core.auth import User, get_current_user
from app.routers import me
from app.services.quota import QuotaSummary


def test_slow_quota_does_not_block_other_requests(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    released_by_other_request = []

    def slow_summary(*, user_id):
        started.set()
        released_by_other_request.append(release.wait(timeout=2))
        return QuotaSummary("beta", 3, 1, 15, 0, 3, 12)

    monkeypatch.setattr(me, "get_quota_summary", slow_summary)
    app = FastAPI()
    app.include_router(me.router)
    app.dependency_overrides[get_current_user] = lambda: User(
        id="test-user", email="test@example.com", access_token="test"
    )

    @app.get("/probe")
    async def probe():
        release.set()
        return {"ok": True}

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            quota = asyncio.create_task(client.get("/me/quota"))
            try:
                async def wait_started():
                    while not started.is_set():
                        await asyncio.sleep(0.005)

                await asyncio.wait_for(wait_started(), timeout=3)
                assert (await client.get("/probe")).status_code == 200
                response = await quota
                assert response.status_code == 200
                assert response.json()["generation_remaining"] == 12
                assert released_by_other_request == [True]
            finally:
                release.set()
                await quota

    asyncio.run(run())
