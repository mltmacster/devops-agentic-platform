"""Tests for the Workspace Orchestrator API.

Uses pytest + asyncio with an in-memory SQLite database to verify:
  • Create workspace (POST /workspaces) — success + uniqueness validation
  • Get workspace details (GET /workspaces/{id}) — including sandbox list
  • Update workspace name (PUT /workspaces/{id}/name)
  • Delete workspace (DELETE /workspaces/{id}) — soft delete with grace period
  • Health endpoints (GET /health/live and /health/ready)

Run: pytest tests/test_workspace_api.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport

# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pytest
from src.api.workspace.main import app


async def _create_client() -> AsyncClient:
    """Create an async HTTP client pointing at the workspace API."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_workspace_success():
    """POST /workspaces should create a workspace and return 201."""
    from src.database import init_db, drop_db

    # Setup: clean and initialize DB
    await drop_db()
    await init_db()

    # Test: create workspace
    client = await _create_client()
    resp = await client.post(
        "/workspaces",
        json={"name": "alpha-workspace", "tier": "pro"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "alpha-workspace"
    assert data["tier"] == "pro"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_workspace_duplicate_name():
    """POST /workspaces should reject duplicate names with 409."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # First creation succeeds
    create_resp = await client.post("/workspaces", json={"name": "unique-name"})
    assert create_resp.status_code == 201

    # Second creation fails with 409
    resp = await client.post(
        "/workspaces",
        json={"name": "unique-name"},
    )

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_workspace_success():
    """GET /workspaces/{id} should return workspace details including sandboxes."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/workspaces",
        json={"name": "beta-workspace"},
    )
    ws_id = create_resp.json()["id"]

    # Get it
    resp = await client.get(f"/workspaces/{ws_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == ws_id
    assert data["name"] == "beta-workspace"
    assert data["tier"] == "free"  # default tier
    assert data["sandboxes"] == []


@pytest.mark.asyncio
async def test_get_workspace_not_found():
    """GET /workspaces/{id} should return 404 for unknown IDs."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    resp = await client.get("/workspaces/nonexistent-id")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_workspace_name():
    """PUT /workspaces/{id} should update the workspace name."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/workspaces",
        json={"name": "original-name"},
    )
    ws_id = create_resp.json()["id"]

    # Update name
    resp = await client.put(
        f"/workspaces/{ws_id}",
        json={"name": "renamed-name"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "renamed-name"


@pytest.mark.asyncio
async def test_update_workspace_name_duplicate():
    """PUT /workspaces/{id} should reject names that conflict with existing workspaces."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create two workspaces
    await client.post("/workspaces", json={"name": "first-name"})
    resp2 = await client.post("/workspaces", json={"name": "second-name"})
    ws_id = resp2.json()["id"]

    # Try to rename to an existing name
    resp = await client.put(
        f"/workspaces/{ws_id}",
        json={"name": "first-name"},
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_workspace():
    """DELETE /workspaces/{id} should soft-delete and return 204."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/workspaces",
        json={"name": "to-delete"},
    )
    ws_id = create_resp.json()["id"]

    # Delete
    resp = await client.delete(f"/workspaces/{ws_id}")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_workspace_not_found():
    """DELETE /workspaces/{id} should return 404 for unknown IDs."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    resp = await client.delete("/workspaces/does-not-exist")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_live():
    """GET /health/live should return 200 with status=alive."""
    client = await _create_client()
    resp = await client.get("/health/live")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready():
    """GET /health/ready should return 200 with status=ready."""
    from src.database import init_db

    await init_db()  # Ensure DB is initialized for health check
    client = await _create_client()
    resp = await client.get("/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_workspace_lifecycle_full():
    """End-to-end lifecycle: create → get → update → delete."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # 1. Create
    create_resp = await client.post(
        "/workspaces",
        json={"name": "lifecycle-test", "tier": "enterprise"},
    )
    assert create_resp.status_code == 201
    ws_id = create_resp.json()["id"]

    # 2. Get (verify creation)
    get_resp = await client.get(f"/workspaces/{ws_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["tier"] == "enterprise"

    # 3. Update name
    update_resp = await client.put(
        f"/workspaces/{ws_id}",
        json={"name": "lifecycle-test-renamed"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "lifecycle-test-renamed"

    # 4. Delete
    delete_resp = await client.delete(f"/workspaces/{ws_id}")
    assert delete_resp.status_code == 204

    # 5. Verify it's gone
    not_found_resp = await client.get(f"/workspaces/{ws_id}")
    assert not_found_resp.status_code == 404
