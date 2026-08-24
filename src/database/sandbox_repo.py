"""
DAP Sandbox Repository — Data Access Layer

Repository pattern: isolates all database queries from business logic.
"""

from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Sandbox


class SandboxRepository:
    """Data access for sandbox entities."""

    def __init__(self, session):
        self._session = session

    # ─── CREATE ──────────────────────────────

    async def create(self, workspace_id: str, stack: str = "python") -> Sandbox:
        """Create a new sandbox instance record."""
        import uuid
        
        sandbox = Sandbox(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            stack=stack,
        )
        self._session.add(sandbox)
        await self._session.flush()  # flush so we can load relationships
        return sandbox

    # ─── READ ────────────────────────────────

    async def get_by_id(self, sandbox_id: str) -> Optional[Sandbox]:
        """Fetch a single sandbox by ID."""
        result = await self._session.execute(
            select(Sandbox).where(Sandbox.id == sandbox_id)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: str, limit: int = 50) -> list[Sandbox]:
        """List all sandboxes for a workspace."""
        result = await self._session.execute(
            select(Sandbox)
            .where(Sandbox.workspace_id == workspace_id)
            .limit(limit)
        )
        return result.scalars().all()

    # ─── UPDATE (state transitions) ──────────

    async def update_state(self, sandbox_id: str, state: str) -> Optional[Sandbox]:
        """Transition a sandbox to a new state."""
        stmt = (
            update(Sandbox)
            .where(Sandbox.id == sandbox_id)
            .values(state=state)
        )
        result = await self._session.execute(stmt)
        if result.rowcount == 0:
            return None

        updated = await self.get_by_id(sandbox_id)
        if updated:
            await self._session.refresh(updated)
        return updated

    # ─── DELETE ──────────────────────────────

    async def delete(self, sandbox_id: str) -> bool:
        """Delete a stopped/suspended sandbox."""
        stmt = delete(Sandbox).where(Sandbox.id == sandbox_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
