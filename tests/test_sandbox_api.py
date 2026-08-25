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


# ─── Engine wiring: the API drives the execution backend (SOLUTION 37) ───

from src.api.sandbox import main as sandbox_main
from src.sandbox_engine import SandboxLifecycleManager
from fake_backends import FakeStateBackend


@pytest.fixture()
def fake_state_engine(monkeypatch):
    """Swap the process-wide engine for a state-tracking fake backend.

    Deterministic and cross-platform; monkeypatch restores the previous
    engine after each test.
    """
    backend = FakeStateBackend()
    monkeypatch.setattr(
        sandbox_main, "_engine", SandboxLifecycleManager(backend=backend)
    )
    return backend


@pytest.mark.asyncio
async def test_create_persists_container_id(fake_state_engine):
    """Create must actually create the container and persist its id."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    resp = await client.post(
        "/sandboxes", json={"workspace_id": "ws-ci", "stack": "python"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "creating"  # container created, not yet started
    assert data["tier"] == "basic"
    assert data["container_id"] == "cid-" + data["id"][:8]
    assert fake_state_engine.containers[data["container_id"]] == "created"

    status = (await client.get(f"/sandboxes/{data['id']}/status")).json()
    assert status["status"] == "creating"
    assert status["runtime"] == "fake-state"
    assert status["container_id"] == data["container_id"]


@pytest.mark.asyncio
async def test_api_full_lifecycle_state_tolerance(fake_state_engine):
    """Full lifecycle through the API against a podman-semantics fake.

    Mirrors the fake-podman end-to-end test in test_sandbox_backends.py but
    exercises the DB-persisted container_id path (the API is the source of
    truth; the process registry is ephemeral).
    """
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    data = (await client.post("/sandboxes", json={"workspace_id": "ws-full"})).json()
    sb_id, cid = data["id"], data["container_id"]

    async def db_state():
        return (await client.get(f"/sandboxes/{sb_id}/status")).json()["status"]

    # creating → running
    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 204
    assert fake_state_engine.state(cid) == "running"
    assert await db_state() == "running"

    # running → stopped
    assert (await client.post(f"/sandboxes/{sb_id}/stop")).status_code == 204
    assert fake_state_engine.state(cid) == "exited"
    assert await db_state() == "stopped"

    # stopped → suspended: the container is already exited, so this must be a
    # no-op success (real podman cannot pause it — SOLUTION 36)
    assert (await client.post(f"/sandboxes/{sb_id}/suspend")).status_code == 204
    assert fake_state_engine.state(cid) == "exited"
    assert fake_state_engine.count("pause") == 0
    assert await db_state() == "suspended"

    # suspended → running: must (re)START the exited container
    assert (await client.post(f"/sandboxes/{sb_id}/resume")).status_code == 204
    assert fake_state_engine.state(cid) == "running"
    assert await db_state() == "running"

    # running → suspended: real pause; resume unpauses
    assert (await client.post(f"/sandboxes/{sb_id}/suspend")).status_code == 204
    assert fake_state_engine.state(cid) == "paused"
    assert (await client.post(f"/sandboxes/{sb_id}/resume")).status_code == 204
    assert fake_state_engine.state(cid) == "running"

    # stop and delete
    assert (await client.post(f"/sandboxes/{sb_id}/stop")).status_code == 204
    assert (await client.delete(f"/sandboxes/{sb_id}")).status_code == 204
    assert cid not in fake_state_engine.containers
    assert (await client.get(f"/sandboxes/{sb_id}/status")).status_code == 404

    # Exact podman op sequence, same invariants as the fake-podman test
    assert fake_state_engine.count("create") == 1
    assert fake_state_engine.count("start") == 2
    assert fake_state_engine.count("stop") == 2
    assert fake_state_engine.count("pause") == 1
    assert fake_state_engine.count("unpause") == 1
    assert fake_state_engine.count("remove") == 1


@pytest.mark.asyncio
async def test_api_create_failure_parks_error(monkeypatch):
    """A failed real-container create parks the sandbox in 'error' (409-free,
    trackable, deletable) — matching the manager's no-container semantics."""
    from src.database import init_db, drop_db

    class FailingCreate(FakeStateBackend):
        name = "failing-create"

        def create(self, sandbox_id, image, mem_gb, cpu):
            self.calls.append("create")
            return None

    monkeypatch.setattr(
        sandbox_main, "_engine", SandboxLifecycleManager(backend=FailingCreate())
    )
    await drop_db()
    await init_db()

    client = await _create_client()
    data = (await client.post("/sandboxes", json={"workspace_id": "ws-err"})).json()
    assert data["status"] == "error"
    assert data["container_id"] is None

    # ops on a containerless sandbox fail → 502, state stays 'error'
    assert (await client.post(f"/sandboxes/{data['id']}/start")).status_code == 502
    status = (await client.get(f"/sandboxes/{data['id']}/status")).json()
    assert status["status"] == "error"

    # but delete always cleans up
    assert (await client.delete(f"/sandboxes/{data['id']}")).status_code == 204
    assert (await client.get(f"/sandboxes/{data['id']}/status")).status_code == 404


@pytest.mark.asyncio
async def test_api_vanished_container_parks_error(fake_state_engine):
    """Container lost on the host (e.g. podman system reset) → the next op
    fails with 502 and the sandbox parks in 'error' (drift recovery)."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    data = (await client.post("/sandboxes", json={"workspace_id": "ws-lost"})).json()
    sb_id, cid = data["id"], data["container_id"]
    assert (await client.post(f"/sandboxes/{sb_id}/start")).status_code == 204
    assert (await client.post(f"/sandboxes/{sb_id}/suspend")).status_code == 204

    del fake_state_engine.containers[cid]  # host reset: container is gone

    assert (await client.post(f"/sandboxes/{sb_id}/resume")).status_code == 502
    status = (await client.get(f"/sandboxes/{sb_id}/status")).json()
    assert status["status"] == "error"

    # still deletable
    assert (await client.delete(f"/sandboxes/{sb_id}")).status_code == 204


@pytest.mark.asyncio
async def test_invalid_tier_rejected():
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    resp = await client.post(
        "/sandboxes", json={"workspace_id": "ws-tier", "tier": "mega"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_null_backend_sentinel():
    """Dev/CI default (null backend): create persists the sentinel container id."""
    from src.database import init_db, drop_db

    await drop_db()
    await init_db()

    client = await _create_client()
    data = (await client.post("/sandboxes", json={"workspace_id": "ws-null"})).json()
    assert data["status"] == "creating"
    assert data["container_id"].startswith("null-")
