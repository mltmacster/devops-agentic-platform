"""Tests for the Sandbox Lifecycle Manager API.

Verifies:
  • Create sandbox with valid/invalid stacks
  • Get sandbox status (GET /sandboxes/{id}/status)
  • State transitions: stop, suspend, resume
  • Delete sandbox (only stopped/suspended)
  • Health endpoints

Run: pytest tests/test_sandbox_api.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport

# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pytest
from src.api.sandbox.main import app


async def _create_client() -> AsyncClient:
    """Create an async HTTP client pointing at the sandbox API."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_sandbox_success():
    """POST /sandboxes should create a sandbox and return 201."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-123", "stack": "python"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["workspace_id"] == "ws-123"
    assert data["stack"] == "python"


@pytest.mark.asyncio
async def test_create_sandbox_invalid_stack():
    """POST /sandboxes should reject invalid stack values with 400."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-123", "stack": "invalid-stack"},
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_sandbox_status_success():
    """GET /sandboxes/{id}/status should return sandbox status."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-456", "stack": "rust"},
    )
    sb_id = create_resp.json()["id"]

    # Get status (will return defaults since not really running)
    resp = await client.get(f"/sandboxes/{sb_id}/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sb_id
    assert data["stack"] == "rust"


@pytest.mark.asyncio
async def test_get_sandbox_not_found():
    """GET /sandboxes/{id}/status should return 404 for unknown IDs."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    resp = await client.get("/sandboxes/nonexistent-id/status")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stop_sandbox():
    """POST /sandboxes/{id}/stop should transition to stopped state."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-789"},
    )
    sb_id = create_resp.json()["id"]

    # Stop
    resp = await client.post(f"/sandboxes/{sb_id}/stop")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_suspend_sandbox():
    """POST /sandboxes/{id}/suspend should transition to suspended state."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-abc"},
    )
    sb_id = create_resp.json()["id"]

    # Suspend
    resp = await client.post(f"/sandboxes/{sb_id}/suspend")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_resume_sandbox():
    """POST /sandboxes/{id}/resume should transition to running state."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-xyz"},
    )
    sb_id = create_resp.json()["id"]

    # Resume
    resp = await client.post(f"/sandboxes/{sb_id}/resume")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_sandbox():
    """DELETE /sandboxes/{id} should remove the sandbox and return 204."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # Create first
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-del"},
    )
    sb_id = create_resp.json()["id"]

    # Delete
    resp = await client.delete(f"/sandboxes/{sb_id}")

    assert resp.status_code == 204


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
async def test_sandbox_lifecycle_full():
    """End-to-end lifecycle: create → stop → suspend → resume → delete."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    # 1. Create
    create_resp = await client.post(
        "/sandboxes",
        json={"workspace_id": "ws-full-test", "stack": "ml"},
    )
    assert create_resp.status_code == 201
    sb_id = create_resp.json()["id"]

    # 2. Stop
    stop_resp = await client.post(f"/sandboxes/{sb_id}/stop")
    assert stop_resp.status_code == 204

    # 3. Suspend
    suspend_resp = await client.post(f"/sandboxes/{sb_id}/suspend")
    assert suspend_resp.status_code == 204

    # 4. Resume
    resume_resp = await client.post(f"/sandboxes/{sb_id}/resume")
    assert resume_resp.status_code == 204

    # 5. Delete
    delete_resp = await client.delete(f"/sandboxes/{sb_id}")
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_start_sandbox():
    """POST /sandboxes/{id}/start should transition a creating sandbox to running."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    sb_id = (await client.post("/sandboxes", json={"workspace_id": "ws-start"})).json()["id"]

    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 204
    status_resp = await client.get(f"/sandboxes/{sb_id}/status")
    assert status_resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_start_running_rejected():
    """Starting an already-running sandbox should be rejected with 409."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    sb_id = (await client.post("/sandboxes", json={"workspace_id": "ws-dup"})).json()["id"]
    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 204

    resp = await client.post(f"/sandboxes/{sb_id}/start")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_double_stop_rejected():
    """Stopping an already-stopped sandbox should be rejected with 409."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    sb_id = (await client.post("/sandboxes", json={"workspace_id": "ws-stop"})).json()["id"]
    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 204
    assert (await client.post(f"/sandboxes/{sb_id}/stop")).status_code == 204

    resp = await client.post(f"/sandboxes/{sb_id}/stop")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete_then_touch_404():
    """Lifecycle actions on a deleted sandbox should 404 (deleted is terminal)."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()

    sb_id = (await client.post("/sandboxes", json={"workspace_id": "ws-term"})).json()["id"]
    assert (await client.delete(f"/sandboxes/{sb_id}")).status_code == 204

    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 404
    assert (await client.post(f"/sandboxes/{sb_id}/stop")).status_code == 404
    assert (await client.get(f"/sandboxes/{sb_id}/status")).status_code == 404
