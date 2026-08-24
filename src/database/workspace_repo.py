"""
DAP Workspace Repository — Data Access Layer

Repository pattern: isolates all database queries from business logic.
"""

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Workspace


class WorkspaceRepository:
    """Data access for workspace entities."""

    def __init__(self, session):
        self._session = session

    # ─── CREATE ──────────────────────────────

    async def create(self, name: str, tier: str = "free") -> Workspace:
        """Create a new workspace. Returns the persisted instance."""
        workspace = Workspace(
            id=str(__import__('uuid').uuid4()),
            name=name,
            tier=tier,
        )
        self._session.add(workspace)
        await self._session.flush()  # flush so we can load relationships
        return workspace

    # ─── READ ────────────────────────────────

    async def get_by_id(self, workspace_id: str) -> Optional[Workspace]:
        """Fetch a single workspace by ID."""
        result = await self._session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Workspace]:
        """Fetch a workspace by its unique name."""
        result = await self._session.execute(
            select(Workspace).where(Workspace.name == name)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50) -> list[Workspace]:
        """List all active workspaces, newest first."""
        result = await self._session.execute(
            select(Workspace)
            .where(Workspace.status == "active")
            .order_by(Workspace.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_sandbox_count(self, workspace_id: str) -> int:
        """Count running sandboxes for a workspace."""
        result = await self._session.execute(
            select(__import__('sqlalchemy').func.count()).select_from(__import__('src.database.models').Sandbox).where(__import__('src.database.models').Sandbox.workspace_id == workspace_id)
        )
        return result.scalar_one() or 0

    # ─── UPDATE ──────────────────────────────

    async def update_name(self, workspace_id: str, name: str) -> Optional[Workspace]:
        """Update the workspace name."""
        # Check for uniqueness before updating (avoids database constraint errors)
        existing = await self.get_by_name(name)
        if existing and existing.id != workspace_id:
            return None

        stmt = (
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(name=name)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None

        updated = await self.get_by_id(workspace_id)
        if updated:
            await self._session.refresh(updated)
        return updated

    async def update_tier(self, workspace_id: str, tier: str) -> Optional[Workspace]:
        """Update the workspace tier."""
        stmt = (
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(tier=tier)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None

        updated = await self.get_by_id(workspace_id)
        if updated:
            await self._session.refresh(updated)
        return updated

    # ─── DELETE (soft delete with grace period) ──

    async def soft_delete(self, workspace_id: str) -> Optional[Workspace]:
        """Soft-delete a workspace. Sets deleted_at timestamp."""
        from sqlalchemy import update as _update

        stmt = (
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(status="deleted", deleted_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc))
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None

        updated = await self.get_by_id(workspace_id)
        if updated:
            await self._session.refresh(updated)
        return updated
