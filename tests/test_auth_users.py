"""Tests for real auth persistence — user store, PBKDF2, JWT, strict/dev modes.

Run: TESTING=1 pytest tests/test_auth_users.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from src.api.auth.main import app
from src.api.auth.credentials import (
    create_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from src.database import drop_db, init_db


EMAIL = "alice@example.com"
PASSWORD = "sup3r-secret-pw"


async def _client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _fresh_db():
    await drop_db()
    await init_db()


# ─── Credentials unit tests (no DB) ─────────────────


def test_password_hash_roundtrip():
    stored = hash_password("hunter22hunter")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("hunter22hunter", stored) is True
    assert verify_password("wrong", stored) is False


def test_password_verify_rejects_malformed():
    assert verify_password("x", "not-a-valid-hash") is False
    assert verify_password("x", "") is False


def test_jwt_roundtrip_and_reject():
    access, refresh = create_token_pair("u1", "a@b.c", "admin")
    payload = decode_token(access, typ="access")
    assert payload["sub"] == "u1"
    assert payload["email"] == "a@b.c"
    assert payload["role"] == "admin"

    # wrong type rejected
    assert decode_token(access, typ="refresh") is None
    # tampered signature rejected
    tampered = access[:-4] + ("aaaa" if not access.endswith("aaaa") else "bbbb")
    assert decode_token(tampered, typ="access") is None
    # garbage rejected
    assert decode_token("not.a.jwt") is None


# ─── Register / login / refresh / me ─────────────────


@pytest.mark.asyncio
async def test_register_first_user_is_admin():
    await _fresh_db()
    client = await _client()
    resp = await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == EMAIL
    assert data["role"] == "admin"
    assert data["id"]


@pytest.mark.asyncio
async def test_register_second_user_is_developer():
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": "first@example.com", "password": PASSWORD})
    resp = await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 201
    assert resp.json()["role"] == "developer"


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict():
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    resp = await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_rejected():
    await _fresh_db()
    client = await _client()
    resp = await client.post("/auth/register", json={"email": EMAIL, "password": "short"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_registered_user_returns_real_jwt():
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})

    resp = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert not token.startswith("mock_")
    payload = decode_token(token, typ="access")
    assert payload is not None and payload["email"] == EMAIL


@pytest.mark.asyncio
async def test_login_wrong_password_dev_mode_fail_open():
    """Dev mode (default): unknown/wrong credentials still get mock tokens."""
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})

    resp = await client.post("/auth/login", json={"email": EMAIL, "password": "WRONG-password"})
    assert resp.status_code == 200  # fail-open dev behavior
    assert resp.json()["access_token"].startswith("mock_")


@pytest.mark.asyncio
async def test_login_strict_rejects_wrong_password(monkeypatch):
    monkeypatch.setenv("DAP_AUTH_STRICT", "1")
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})

    resp = await client.post("/auth/login", json={"email": EMAIL, "password": "WRONG-password"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_strict_rejects_unknown_user(monkeypatch):
    monkeypatch.setenv("DAP_AUTH_STRICT", "1")
    await _fresh_db()
    client = await _client()
    resp = await client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_for_registered_user():
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})

    login = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    refresh = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_refresh = resp.json()["refresh_token"]
    payload = decode_token(new_refresh, typ="refresh")
    assert payload is not None and payload["email"] == EMAIL


@pytest.mark.asyncio
async def test_me_with_real_token_returns_registered_user():
    await _fresh_db()
    client = await _client()
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    login = await client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    token = login.json()["access_token"]

    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == EMAIL
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_strict_without_token_401(monkeypatch):
    monkeypatch.setenv("DAP_AUTH_STRICT", "1")
    await _fresh_db()
    client = await _client()
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_dev_without_token_legacy_profile():
    await _fresh_db()
    client = await _client()
    resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "dev@example.com"
