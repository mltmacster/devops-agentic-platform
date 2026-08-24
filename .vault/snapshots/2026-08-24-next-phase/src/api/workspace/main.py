"""Workspace Orchestrator — Multi-tenant workspace lifecycle management.

Uses async SQLAlchemy + PostgreSQL for persistent storage.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field

# ─── Database imports (must be top-level) ──────────────
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.database import get_session
from src.database.models import Workspace, WorkspaceQuota
from src.database.workspace_repo import WorkspaceRepository


# ─── Models ──────────────────────────────────

class CreateWorkspaceRequest(BaseModel):
    """POST /workspaces — create a new workspace."""

    name: str = Field(..., min_length=3, max_length=128)
    tier: str = Field(default="free", description="Subscription tier: free | pro | enterprise")


class CreateWorkspaceResponse(BaseModel):
    """POST /workspaces — created workspace."""

    id: str
    name: str
    tier: str
    status: str = "active"


class WorkspaceDetail(BaseModel):
    """GET /workspaces/{id} — workspace details."""

    id: str
    name: str
    tier: str
    status: str
    sandboxes: list[dict]
    quota: dict

    @classmethod
    def from_model(cls, workspace):
        """Build response from SQLAlchemy model."""
        return cls(
            id=workspace.id,
            name=workspace.name,
            tier=workspace.tier,
            status=workspace.status,
            sandboxes=[{
                "id": s.id,
                "state": s.state,
                "stack": s.stack,
                "cpu_cores_used": round(s.cpu_cores_used, 2),
                "memory_mb_used": s.memory_mb_used,
            } for s in workspace.sandboxes],
            quota={
                "max_sandboxes": workspace.tier,  # simplified; in prod: fetch from quota table
                "cpu_gb": round(getattr(workspace, '_quota_cpu_gb', 2.0), 1),
                "memory_gb": round(getattr(workspace, '_quota_mem_gb', 4.0), 1),
                "disk_gb": round(getattr(workspace, '_quota_disk_gb', 20.0), 1),
            },
        )


class UpdateWorkspaceRequest(BaseModel):
    """PUT /workspaces/{id} — update workspace."""

    name: str | None = Field(None, min_length=3, max_length=128)


# ─── App ──────────────────────────────────────
app = FastAPI(
    title="DAP Workspace Orchestrator",
    description="Multi-tenant workspace lifecycle management",
    version="1.0.0",
)


# ─── Dependency: session factory ──────────────

async def get_session_dependency():
    """FastAPI dependency that yields a database session."""
    async with get_session() as session:
        yield session


# ─── Endpoints ────────────────────────────────

@app.post(
    "/workspaces",
    response_model=CreateWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    session=Depends(get_session_dependency),
):
    """Create a new workspace with the specified tier.

    Creates a workspace record in PostgreSQL and returns its ID for downstream use.
    """
    # Validate tier
    valid_tiers = {"free", "pro", "enterprise"}
    if payload.tier not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{payload.tier}'. Must be one of: {', '.join(sorted(valid_tiers))}",
        )

    # Check name uniqueness
    repo = WorkspaceRepository(session)
    existing = await repo.get_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A workspace named '{payload.name}' already exists.",
        )

    # Create
    workspace = await repo.create(name=payload.name, tier=payload.tier)

    return CreateWorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        tier=workspace.tier,
    )


@app.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceDetail,
    summary="Get workspace details",
)
async def get_workspace(
    workspace_id: str,
    session=Depends(get_session_dependency),
):
    """Return detailed info for the given workspace, including sandbox list and quota."""
    repo = WorkspaceRepository(session)

    # Fetch workspace with eager-loaded sandboxes for efficiency
    result = await session.execute(
        select(Workspace)
        .options(joinedload(Workspace.sandboxes))
        .where(Workspace.id == workspace_id)
    )
    workspace = result.scalars().unique().one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    # Check if workspace is deleted (soft delete)
    if workspace.status == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' has been deleted.",
        )

    return WorkspaceDetail.from_model(workspace)


@app.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace (30-day grace period)",
)
async def delete_workspace(
    workspace_id: str,
    session=Depends(get_session_dependency),
):
    """Delete a workspace. Sets to 'deleted' status (soft delete).

    In production, this would:
      1. Check the user has deletion permissions (RBAC)
      2. Gracefully stop all associated sandboxes
      3. Soft-delete the workspace record
      4. Schedule a permanent purge after 30 days via Celery beat
    """
    repo = WorkspaceRepository(session)

    result = await repo.soft_delete(workspace_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )


@app.put(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceDetail,
    summary="Update workspace settings",
)
async def update_workspace(
    workspace_id: str,
    updates: UpdateWorkspaceRequest,
    session=Depends(get_session_dependency),
):
    """Update a workspace's name or tier.

    Only `name` is supported in this implementation. Tier changes require
    a separate PUT endpoint with validation and quota recalculation.
    """
    repo = WorkspaceRepository(session)

    # Verify the workspace exists first
    existing = await repo.get_by_id(workspace_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace '{workspace_id}' not found.",
        )

    # Update name if provided
    if updates.name is not None:
        updated = await repo.update_name(workspace_id, updates.name)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A workspace named '{updates.name}' already exists.",
            )

    # Return refreshed workspace detail
    result = await session.execute(
        select(Workspace)
        .options(joinedload(Workspace.sandboxes))
        .where(Workspace.id == workspace_id)
    )
    workspace = result.scalars().unique().one_or_none()

    return WorkspaceDetail.from_model(workspace)


@app.get("/health/live", status_code=status.HTTP_200_OK)
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def health_ready():
    """Check if the workspace service can connect to PostgreSQL."""
    try:
        async with get_session() as session:
            from sqlalchemy import select as _select
            await session.execute(_select(1))
    except Exception:
        return {"status": "not_ready", "reason": "database_unreachable"}

    return {"status": "ready"}
