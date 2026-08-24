"""
DAP Domain Models — SQLAlchemy 2.0 async models

Uses declarative base for all domain entities.
"""

from datetime import UTC, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─── Base ─────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─── Enums ────────────────────────────────────
class WorkspaceTier(str):  # noqa: A003
    """Workspace subscription tiers with resource limits."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class WorkspaceStatus(str):  # noqa: A003

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


# ─── Quota Config (shared across workspace tiers) ──

# Seed data for the quota table
QUOTA_SEED_DATA = [
    {"tier": "free", "max_sandboxes": 1, "cpu_gb": 0.5, "memory_gb": 1.0, "disk_gb": 5.0},
    {"tier": "pro", "max_sandboxes": 3, "cpu_gb": 2.0, "memory_gb": 4.0, "disk_gb": 20.0},
    {"tier": "enterprise", "max_sandboxes": 10, "cpu_gb": 8.0, "memory_gb": 32.0, "disk_gb": 100.0},
]


class WorkspaceQuota(Base):
    """Per-tier resource quotas for sandbox creation limits."""

    __tablename__ = "workspace_quotas"

    tier: Mapped[str] = mapped_column(String(20), primary_key=True)
    max_sandboxes: Mapped[int] = mapped_column(Integer, default=0)
    cpu_gb: Mapped[float] = mapped_column(Float, default=0.0)
    memory_gb: Mapped[float] = mapped_column(Float, default=0.0)
    disk_gb: Mapped[float] = mapped_column(Float, default=0.0)

    @classmethod
    def seed(cls, session):
        """Insert default quota tiers if not present."""
        for data in QUOTA_SEED_DATA:
            session.merge(WorkspaceQuota(**data))


# ─── Workspace (parent) ───────────────────────
class Workspace(Base):
    """Multi-tenant workspace with sandbox quota tracking."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    sandboxes: Mapped[list["Sandbox"]] = relationship(
        "Sandbox", back_populates="workspace", cascade="all, delete-orphan"
    )

    @property
    def sandbox_count(self) -> int:
        """Current number of sandboxes for this workspace."""
        return len(self.sandboxes)


# ─── Sandbox (child of a workspace) ───────────
class Sandbox(Base):
    """A sandbox VM instance belonging to a workspace."""

    __tablename__ = "sandboxes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stack: Mapped[str] = mapped_column(String(20), nullable=False)  # python, rust, nodejs, ml
    state: Mapped[str] = mapped_column(String(20), nullable=False, default='creating')  # creating, running, stopped, suspended
    cpu_cores_used: Mapped[float] = mapped_column(Float, default=0.0)
    memory_mb_used: Mapped[int] = mapped_column(Integer, default=0)
    disk_gb_used: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    workspace = relationship("Workspace", back_populates="sandboxes")


# ─── Seed helper ──────────────────────────────
def seed_all(session):
    """Seed all tables."""
    WorkspaceQuota.seed(session)
