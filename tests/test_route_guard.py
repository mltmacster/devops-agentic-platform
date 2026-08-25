"""Tests for the strict-mode route guard (SOLUTION 39).

Covers the full monolith app (src.main:app) with the StrictAuthMiddleware
installed: dev mode stays fail-open; strict mode fails closed on data routes,
keeps the public allowlist open, and closes registration after the first
user. Run: TESTING=1 pytest tests/test_route_guard.py -v
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app  # the monolith — includes the route guard
from src.database import drop_db, init_db


EMAIL_1 = "first@example.com"
EMAIL_2 = "second@example.com"
PASSWORD = "RouteGuard-Passw0rd!"


@pytest.fixture
def strict(monkeypatch):
    monkeypatch.setenv("DAP_AUTH_STRICT", "1")
    monkeypatch.setenv("DAP_JWT_SECRET", "route-guard-test-secret")


@pytest.fixture
def dev(monkeypatch):
    monkeypatch.setenv("DAP_AUTH_STRICT", "0")
    monkeypatch.setenv("DAP_JWT_SECRET", "route-guard-test-secret")


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _fresh_db():
    await drop_db()
    await init_db()


async def _register(client: AsyncClient, email: str):
    return await client.post(
        "/api/auth/auth/register",
        json={"email": email, "password": PASSWORD},
    )


# ─── Dev mode stays fail-open ────────────────────────────────


@pytest.mark.asyncio
async def test_dev_mode_anonymous_data_route_ok(dev):
    await _fresh_db()
    async with await _client() as client:
        assert (await client.get("/api/workspace/workspaces")).status_code == 200


@pytest.mark.asyncio
async def test_dev_mode_open_registration(dev):
    await _fresh_db()
    async with await _client() as client:
        assert (await _register(client, EMAIL_1)).status_code == 201
        assert (await _register(client, EMAIL_2)).status_code == 201


# ─── Strict mode: fail-closed on data routes ─────────────────


@pytest.mark.asyncio
async def test_strict_blocks_anonymous_data_routes(strict):
    await _fresh_db()
    async with await _client() as client:
        assert (await client.get("/api/workspace/workspaces")).status_code == 401
        assert (await client.get("/api/sandbox/sandboxes/x/status")).status_code == 401
        assert (await client.get("/api/ide/stats")).status_code == 401
        assert (await client.get("/api/agentic/llm/status")).status_code == 401


@pytest.mark.asyncio
async def test_strict_rejects_garbage_token(strict):
    await _fresh_db()
    async with await _client() as client:
        r = await client.get(
            "/api/workspace/workspaces",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_strict_allows_valid_token(strict):
    await _fresh_db()
    async with await _client() as client:
        assert (await _register(client, EMAIL_1)).status_code == 201
        login = await client.post(
            "/api/auth/auth/login", json={"email": EMAIL_1, "password": PASSWORD}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        r = await client.get(
            "/api/workspace/workspaces",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200


# ─── Strict mode: public allowlist stays open ────────────────


@pytest.mark.asyncio
async def test_strict_public_paths_open(strict):
    await _fresh_db()
    async with await _client() as client:
        assert (await client.get("/health")).status_code == 200
        assert (await client.get("/openapi.json")).status_code == 200
        assert (await client.get("/api/observability/metrics")).status_code == 200
        assert (await client.get("/api/observability/health")).status_code == 200
        assert (await client.get("/api/workspace/health/live")).status_code == 200


# ─── Registration closure (first-user-admin race) ────────────


@pytest.mark.asyncio
async def test_strict_registration_closes_after_first_user(strict):
    await _fresh_db()
    async with await _client() as client:
        assert (await _register(client, EMAIL_1)).status_code == 201
        blocked = await _register(client, EMAIL_2)
        assert blocked.status_code == 403
        assert "closed" in blocked.json()["detail"].lower()


@pytest.mark.asyncio
async def test_strict_first_user_still_able_to_register(strict):
    await _fresh_db()
    async with await _client() as client:
        # Empty identity store: the bootstrap registration must succeed.
        assert (await _register(client, EMAIL_1)).status_code == 201
