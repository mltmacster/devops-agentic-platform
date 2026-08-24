"""Sandbox VM Lifecycle Manager

Manages the full lifecycle of Lite VM instances (Ubuntu 24.04 + Podman/gVisor).

Provides: create, start, stop, suspend, resume, delete operations with
resource limits, guarded by a single lifecycle state machine that the
sandbox API reuses for DB-backed transitions.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class SandboxState(Enum):
    """Sandbox lifecycle states (values match the DB `state` column)."""
    CREATING = auto()
    RUNNING = auto()
    STOPPED = auto()
    SUSPENDED = auto()
    ERROR = auto()
    DELETED = auto()


# ─── Lifecycle State Machine ────────────────────────────────
# Legal transitions per state. CREATING is provisional (the VM has not
# fully booted) so any target is allowed. DELETED is terminal. DELETE is
# legal from every non-terminal state: it destroys or aborts whatever
# exists. Self-transitions are always illegal.
TRANSITIONS: Dict[SandboxState, "set[SandboxState]"] = {
    SandboxState.CREATING: {
        SandboxState.RUNNING, SandboxState.STOPPED, SandboxState.SUSPENDED,
        SandboxState.ERROR, SandboxState.DELETED,
    },
    SandboxState.RUNNING: {
        SandboxState.STOPPED, SandboxState.SUSPENDED,
        SandboxState.ERROR, SandboxState.DELETED,
    },
    SandboxState.STOPPED: {
        SandboxState.RUNNING, SandboxState.SUSPENDED, SandboxState.DELETED,
    },
    SandboxState.SUSPENDED: {
        SandboxState.RUNNING, SandboxState.STOPPED, SandboxState.DELETED,
    },
    SandboxState.ERROR: {
        SandboxState.RUNNING, SandboxState.DELETED,
    },
    SandboxState.DELETED: set(),
}


def can_transition(current: SandboxState, target: SandboxState) -> bool:
    """Return True if moving a sandbox from `current` to `target` is legal."""
    return current != target and target in TRANSITIONS.get(current, set())


def state_from_str(value: str) -> Optional[SandboxState]:
    """Map a state string (e.g. the DB `state` column) to a SandboxState."""
    try:
        return SandboxState[value.upper()]
    except KeyError:
        return None


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
    All state changes are guarded by the TRANSITIONS state machine.
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
        """Start a stopped/suspended/errored sandbox."""
        sandbox = self._transition(sandbox_id, SandboxState.RUNNING)
        if sandbox:
            logger.info("Started sandbox: %s", sandbox)
        return sandbox

    def stop_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Gracefully stop a running sandbox."""
        sandbox = self._transition(sandbox_id, SandboxState.STOPPED)
        if sandbox:
            logger.info("Stopped sandbox: %s", sandbox)
        return sandbox

    def suspend_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Checkpoint and pause a running sandbox."""
        sandbox = self._transition(sandbox_id, SandboxState.SUSPENDED)
        if sandbox:
            logger.info("Suspended sandbox: %s", sandbox)
        return sandbox

    def resume_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Resume a suspended sandbox from checkpoint."""
        sandbox = self._transition(sandbox_id, SandboxState.RUNNING)
        if sandbox:
            logger.info("Resumed sandbox: %s", sandbox)
        return sandbox

    def delete_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Delete a sandbox (destroys or aborts whatever exists)."""
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox is None:
            logger.error("Sandbox %s not found", sandbox_id)
            return None

        if not can_transition(sandbox.status, SandboxState.DELETED):
            logger.warning(
                "Cannot delete sandbox %s (status=%s)", sandbox_id, sandbox.status.name
            )
            return None

        # In production: podman rm --rm <id>
        del self._sandboxes[sandbox_id]
        logger.info("Deleted sandbox: %s", sandbox_id)

        return None

    def _transition(self, sandbox_id: str, target: SandboxState) -> Optional[SandboxInstance]:
        """Apply a guarded state transition to an in-memory sandbox."""
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox is None:
            logger.error("Sandbox %s not found", sandbox_id)
            return None

        if not can_transition(sandbox.status, target):
            logger.warning(
                "Illegal transition %s -> %s for sandbox %s",
                sandbox.status.name, target.name, sandbox_id,
            )
            return None

        sandbox.status = target
        return sandbox

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
        stats = {state: 0 for state in SandboxState}
        for sandbox in self._sandboxes.values():
            stats[sandbox.status] += 1

        return {
            "total": len(self._sandboxes),
            "creating": stats[SandboxState.CREATING],
            "running": stats[SandboxState.RUNNING],
            "stopped": stats[SandboxState.STOPPED],
            "suspended": stats[SandboxState.SUSPENDED],
            "error": stats[SandboxState.ERROR],
        }


def get_sandbox_manager() -> SandboxLifecycleManager:
    """Factory function for the sandbox lifecycle manager."""
    return SandboxLifecycleManager()
