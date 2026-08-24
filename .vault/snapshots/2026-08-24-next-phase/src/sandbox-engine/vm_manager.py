"""Sandbox VM Lifecycle Manager

Manages the full lifecycle of Lite VM instances (Ubuntu 24.04 + Podman/gVisor).

Provides: create, start, stop, suspend, resume, delete operations with resource limits.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class SandboxState(Enum):
    """Sandbox lifecycle states."""
    CREATING = auto()
    RUNNING = auto()
    STOPPED = auto()
    SUSPENDED = auto()
    DELETED = auto()


@dataclass
class SandboxResourceQuota:
    """Resource limits per tier."""
    cpu_cores: float = 1.0
    memory_gb: float = 2.0
    disk_gb: float = 10.0
    max_concurrent_sandboxes: int = 1


@dataclass
class SandboxInstance:
    """Represents a sandbox VM instance."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: SandboxState = SandboxState.CREATING
    tier: str = "basic"
    resources: SandboxResourceQuota = field(default_factory=SandboxResourceQuota)

    def __str__(self) -> str:
        return f"Sandbox({self.id[:8]}..., status={self.status.name}, tier={self.tier})"


class SandboxLifecycleManager:
    """Manages the full lifecycle of Lite VM instances.

    This is a simplified in-memory manager — in production, this would
    communicate with Podman/Kubernetes and track state in PostgreSQL.
    """

    def __init__(self):
        self._sandboxes: Dict[str, SandboxInstance] = {}

    def create_sandbox(self, tier: str = "basic") -> SandboxInstance:
        """Create a new sandbox instance."""
        quota_map = {
            "basic": SandboxResourceQuota(cpu_cores=1.0, memory_gb=2.0, disk_gb=10.0),
            "pro": SandboxResourceQuota(cpu_cores=4.0, memory_gb=8.0, disk_gb=50.0),
            "enterprise": SandboxResourceQuota(cpu_cores=8.0, memory_gb=16.0, disk_gb=200.0),
            "ga": SandboxResourceQuota(cpu_cores=16.0, memory_gb=32.0, disk_gb=500.0),
        }

        quota = quota_map.get(tier, SandboxResourceQuota())
        instance = SandboxInstance(tier=tier, resources=quota)

        self._sandboxes[instance.id] = instance
        logger.info("Created sandbox: %s", instance)

        # In production: Podman create + podman start
        # self._podman_create(instance)

        return instance

    def start_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Start a stopped/suspended sandbox."""
        if sandbox_id not in self._sandboxes:
            logger.error("Sandbox %s not found", sandbox_id)
            return None

        sandbox = self._sandboxes[sandbox_id]
        if sandbox.status == SandboxState.RUNNING:
            logger.warning("Sandbox %s already running", sandbox_id)
            return None

        # In production: Podman start + podman run --checkpoint for resume
        sandbox.status = SandboxState.RUNNING
        logger.info("Started sandbox: %s", sandbox)

        return sandbox

    def stop_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Gracefully stop a running sandbox."""
        if sandbox_id not in self._sandboxes:
            logger.error("Sandbox %s not found", sandbox_id)
            return None

        sandbox = self._sandboxes[sandbox_id]
        if sandbox.status != SandboxState.RUNNING:
            logger.warning("Sandbox %s not running (status=%s)", sandbox_id, sandbox.status.name)
            return None

        # In production: podman stop (SIGTERM wait 30s, then SIGKILL)
        sandbox.status = SandboxState.STOPPED
        logger.info("Stopped sandbox: %s", sandbox)

        return sandbox

    def suspend_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Checkpoint and pause a running sandbox."""
        if sandbox_id not in self._sandboxes:
            return None

        sandbox = self._sandboxes[sandbox_id]
        if sandbox.status != SandboxState.RUNNING:
            return None

        # In production: podman pause + podman checkpoint
        sandbox.status = SandboxState.SUSPENDED
        logger.info("Suspended sandbox: %s", sandbox)

        return sandbox

    def resume_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Resume a suspended sandbox from checkpoint."""
        if sandbox_id not in self._sandboxes:
            return None

        sandbox = self._sandboxes[sandbox_id]
        if sandbox.status != SandboxState.SUSPENDED:
            return None

        # In production: podman resume + restore checkpoint
        sandbox.status = SandboxState.RUNNING
        logger.info("Resumed sandbox: %s", sandbox)

        return sandbox

    def delete_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Delete a stopped/suspended sandbox."""
        if sandbox_id not in self._sandboxes:
            return None

        sandbox = self._sandboxes[sandbox_id]
        if sandbox.status in (SandboxState.RUNNING, SandboxState.SUSPENDED):
            logger.warning("Cannot delete sandbox %s — must stop first", sandbox_id)
            return None

        # In production: podman rm --rm <id>
        del self._sandboxes[sandbox_id]
        logger.info("Deleted sandbox: %s", sandbox)

        return None

    def get_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    def list_sandboxes(self, status: Optional[SandboxState] = None) -> list[SandboxInstance]:
        """List sandboxes, optionally filtered by status."""
        if status:
            return [s for s in self._sandboxes.values() if s.status == status]
        return list(self._sandboxes.values())

    def get_sandbox_usage_stats(self) -> Dict:
        """Get aggregate resource usage statistics."""
        total_sandboxes = len(self._sandboxes)
        running = sum(1 for s in self._sandboxes.values() if s.status == SandboxState.RUNNING)
        stopped = sum(1 for s in self._sandboxes.values() if s.status == SandboxState.STOPPED)
        suspended = sum(1 for s in self._sandboxes.values() if s.status == SandboxState.SUSPENDED)

        return {
            "total": total_sandboxes,
            "running": running,
            "stopped": stopped,
            "suspended": suspended,
        }


def get_sandbox_manager() -> SandboxLifecycleManager:
    """Factory function for the sandbox lifecycle manager."""
    return SandboxLifecycleManager()
