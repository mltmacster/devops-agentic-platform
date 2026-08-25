"""Sandbox Lifecycle Manager — VM boot/shutdown/suspend/resume operations.

Uses async SQLAlchemy + PostgreSQL for persistent sandbox state tracking.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel

# ─── Database imports (must be top-level) ──────────────
from src.database import get_session
from src.database.sandbox_repo import SandboxRepository

# ─── Sandbox engine: lifecycle state machine + execution backend ──────
from src.sandbox_engine import SandboxLifecycleManager, SandboxState, can_transition, state_from_str

# ─── Network imports for URL formatting ──────────────
from src.network import NetworkConfig, build_ide_config_urls


# ─── Models ──────────────────────────────────

class CreateSandboxRequest(BaseModel):
    """POST /sandboxes — create a new sandbox instance."""

    workspace_id: str
    stack: str = "python"  # python | rust | nodejs | ml


class CreateSandboxResponse(BaseModel):
    """POST /sandboxes — created sandbox with network URLs."""

    id: str
    workspace_id: str
    stack: str
    status: str = "creating"
    urls: dict[str, str]


class SandboxStatus(BaseModel):
    """GET /sandboxes/{id}/status — sandbox status."""

    id: str
    status: str  # creating | running | stopped | suspended | error
    stack: str
    runtime: str = "null"  # sandbox execution backend (null | podman | runsc)
    resources: dict


class ResourceUsage(BaseModel):
    """Sandbox resource usage metrics."""

    cpu_cores_used: float
    memory_mb_used: int
    disk_gb_used: float


# ─── App ──────────────────────────────────────
app = FastAPI(
    title="DAP Sandbox Lifecycle Manager",
    description="Sandbox VM lifecycle management (boot/shutdown/suspend/resume)",
    version="1.0.0",
)


# ─── Dependency: session factory ──────────────

async def get_session_dependency():
    """FastAPI dependency that yields a database session."""
    async with get_session() as session:
        yield session


# ─── Sandbox engine (execution backend) ────────────────

_engine: SandboxLifecycleManager | None = None


def _get_engine() -> SandboxLifecycleManager:
    """Lazily-created process-wide sandbox engine (backend auto-selected)."""
    global _engine
    if _engine is None:
        _engine = SandboxLifecycleManager()
    return _engine


async def _validate_transition(
    session, sandbox_id: str, target: SandboxState, action: str
):
    """Fetch the sandbox and guard the lifecycle transition.

    Raises 404 when the sandbox doesn't exist and 409 when the state
    machine rejects the transition. Returns the current sandbox record.
    """
    repo = SandboxRepository(session)
    sandbox = await repo.get_by_id(sandbox_id)
    if sandbox is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox '{sandbox_id}' not found.",
        )

    current = state_from_str(sandbox.state)
    if current is None or not can_transition(current, target):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {action} a sandbox in '{sandbox.state}' state.",
        )
    return sandbox


# ─── Endpoints ────────────────────────────────

@app.post(
    "/sandboxes",
    response_model=CreateSandboxResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sandbox instance",
)
async def create_sandbox(
    payload: CreateSandboxRequest,
    session=Depends(get_session_dependency),
):
    """Create a new sandbox VM with the specified stack.

    In production, this would:
      1. Verify workspace exists and has quota capacity
      2. Spin up a Lite VM (Ubuntu 24.04 + Podman/gVisor)
      3. Install the requested stack (Python/Rust/Node.js/ML)
      4. Register the sandbox record in PostgreSQL
    """
    # Validate stack
    valid_stacks = {"python", "rust", "nodejs", "ml"}
    if payload.stack not in valid_stacks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stack '{payload.stack}'. Must be one of: {', '.join(sorted(valid_stacks))}",
        )

    repo = SandboxRepository(session)
    sandbox = await repo.create(
        workspace_id=payload.workspace_id,
        stack=payload.stack,
    )

    # Generate network URLs for external access
    config = NetworkConfig()
    urls = build_ide_config_urls(
        sandbox_id=sandbox.id,
        base_host=config.base_host,
        ide_port=config.ide_base_port,
        web_port=config.default_port,
        use_https=config.enable_https,
    )

    return CreateSandboxResponse(
        id=sandbox.id,
        workspace_id=payload.workspace_id,
        stack=payload.stack,
        urls=urls,
    )


@app.get(
    "/sandboxes/{sandbox_id}/status",
    response_model=SandboxStatus,
    summary="Get sandbox status and resource usage",
)
async def get_sandbox_status(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Return the current status and resource usage of a sandbox."""
    repo = SandboxRepository(session)

    sandbox = await repo.get_by_id(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox '{sandbox_id}' not found.",
        )

    return SandboxStatus(
        id=sandbox.id,
        status=sandbox.state,
        stack=sandbox.stack,
        runtime=_get_engine().runtime,
        resources={
            "cpu_cores_used": round(sandbox.cpu_cores_used, 2),
            "memory_mb_used": sandbox.memory_mb_used,
            "disk_gb_used": round(sandbox.disk_gb_used, 1),
        },
    )


@app.post(
    "/sandboxes/{sandbox_id}/start",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Start a stopped/suspended/creating sandbox",
)
async def start_sandbox(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Start a sandbox that is stopped, suspended, errored, or still creating.

    In production, this would:
      1. Boot the VM (Podman start) or restore its checkpoint
      2. Transition state to 'running' in the database
    """
    await _validate_transition(session, sandbox_id, SandboxState.RUNNING, "start")
    await SandboxRepository(session).update_state(sandbox_id, "running")


@app.post(
    "/sandboxes/{sandbox_id}/stop",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Gracefully stop a running sandbox",
)
async def stop_sandbox(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Gracefully stop a running sandbox.

    In production, this would:
      1. Send SIGTERM to the sandbox's main process
      2. Wait up to 30s for graceful shutdown
      3. Transition state to 'stopped' in the database
    """
    await _validate_transition(session, sandbox_id, SandboxState.STOPPED, "stop")
    await SandboxRepository(session).update_state(sandbox_id, "stopped")


@app.post(
    "/sandboxes/{sandbox_id}/suspend",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Checkpoint and pause a running sandbox",
)
async def suspend_sandbox(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Checkpoint and pause a running sandbox.

    In production, this would:
      1. Take a snapshot of the VM state (checkpoint)
      2. Pause the VM for later resume
      3. Transition state to 'suspended' in the database
    """
    await _validate_transition(session, sandbox_id, SandboxState.SUSPENDED, "suspend")
    await SandboxRepository(session).update_state(sandbox_id, "suspended")


@app.post(
    "/sandboxes/{sandbox_id}/resume",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Resume a suspended sandbox from checkpoint",
)
async def resume_sandbox(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Resume a suspended sandbox from its checkpoint.

    In production, this would:
      1. Restore the VM from the saved checkpoint
      2. Start the sandbox process
      3. Transition state to 'running' in the database
    """
    await _validate_transition(session, sandbox_id, SandboxState.RUNNING, "resume")
    await SandboxRepository(session).update_state(sandbox_id, "running")


@app.delete(
    "/sandboxes/{sandbox_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a stopped/suspended sandbox",
)
async def delete_sandbox(
    sandbox_id: str,
    session=Depends(get_session_dependency),
):
    """Delete a stopped or suspended sandbox (permanently).

    In production, this would:
      1. Guard the transition (a deleted sandbox cannot be touched again)
      2. Destroy the VM and free resources
      3. Delete the sandbox record from PostgreSQL
    """
    await _validate_transition(session, sandbox_id, SandboxState.DELETED, "delete")

    success = await SandboxRepository(session).delete(sandbox_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox '{sandbox_id}' not found.",
        )


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def health_ready():
    return {"status": "ready"}
