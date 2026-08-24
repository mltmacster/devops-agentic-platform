"""Tests for the Auth Service API.

Uses pytest + httpx async client to verify:
  • POST /auth/login — returns JWT tokens
  • POST /auth/refresh — returns new token pair
  • GET /auth/me — returns user profile with roles/tenants/workspaces
  • POST /auth/check — RBAC permission evaluation (allowed/denied)

Run: pytest tests/test_auth_api.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport


# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pytest
from src.api.auth.main import app


async def _create_client() -> AsyncClient:
    """Create an async HTTP client pointing at the auth API."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_login_returns_tokens():
    """POST /auth/login should return access and refresh tokens."""
    client = await _create_client()

    resp = await client.post(
        "/auth/login",
        json={"email": "dev@example.com", "password": "secret123"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_login_with_invalid_email():
    """POST /auth/login should reject invalid email format."""
    client = await _create_client()

    resp = await client.post(
        "/auth/login",
        json={"email": "not-an-email", "password": "secret123"},
    )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens():
    """POST /auth/refresh should return a new token pair."""
    client = await _create_client()

    resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": "old_refresh_token"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_get_profile_returns_user_data():
    """GET /auth/me should return user profile with tenants and workspaces."""
    client = await _create_client()

    resp = await client.get("/auth/me")

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "email" in data
    assert "role" in data
    assert "tenants" in data
    assert "workspaces" in data


@pytest.mark.asyncio
async def test_rbac_check_granted():
    """POST /auth/check should return allowed=True for high-privilege roles."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "user-123",
            "role": "ga",
            "resource_type": "sandbox",
            "action": "delete",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


@pytest.mark.asyncio
async def test_rbac_check_denied():
    """POST /auth/check should return allowed=False for insufficient permissions."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "user-123",
            "role": "readonly",
            "resource_type": "sandbox",
            "action": "delete",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False


@pytest.mark.asyncio
async def test_rbac_check_invalid_action():
    """POST /auth/check should reject unknown actions with 400."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "user-123",
            "role": "ga",
            "resource_type": "sandbox",
            "action": "invalid-action",
        },
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_health_live():
    """GET /health/live should return 200 with status=alive."""
    client = await _create_client()

    resp = await client.get("/health/live")

    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready():
    """GET /health/ready should return 200 with status=ready."""
    client = await _create_client()

    resp = await client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_rbac_developer_can_delete_sandbox():
    """A developer should NOT be able to delete a sandbox (only read at sandbox level)."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "dev-456",
            "role": "developer",
            "resource_type": "sandbox",
            "action": "delete",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False


@pytest.mark.asyncio
async def test_rbac_developer_can_create_sandbox():
    """A developer SHOULD be able to create a sandbox."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "dev-456",
            "role": "developer",
            "resource_type": "sandbox",
            "action": "create",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


@pytest.mark.asyncio
async def test_rbac_team_admin_can_delete_workspace():
    """A team admin SHOULD be able to delete a workspace."""
    client = await _create_client()

    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "admin-789",
            "role": "team_admin",
            "resource_type": "workspace",
            "action": "delete",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is True


@pytest.mark.asyncio
async def test_rbac_readonly_can_only_read():
    """A readonly user should only have READ permission."""
    client = await _create_client()

    # Read should be allowed
    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "reader-001",
            "role": "readonly",
            "resource_type": "sandbox",
            "action": "read",
        },
    )
    assert resp.json()["allowed"] is True

    # Create should be denied
    resp = await client.post(
        "/auth/check",
        json={
            "user_id": "reader-001",
            "role": "readonly",
            "resource_type": "sandbox",
            "action": "create",
        },
    )
    assert resp.json()["allowed"] is False
