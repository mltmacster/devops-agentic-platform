"""Sandbox Engine — VM lifecycle management for DAP sandboxes.

Provides the lifecycle state machine (single source of truth for legal
state transitions) and an in-memory VM manager for local development.
"""

from .backends import (
    DEFAULT_IMAGE,
    ExecutionBackend,
    NullBackend,
    PodmanBackend,
    select_backend,
)
from .vm_manager import (
    TIERS,
    TRANSITIONS,
    SandboxInstance,
    SandboxLifecycleManager,
    SandboxResourceQuota,
    SandboxState,
    can_transition,
    get_sandbox_manager,
    state_from_str,
)

__all__ = [
    "DEFAULT_IMAGE",
    "ExecutionBackend",
    "NullBackend",
    "PodmanBackend",
    "TIERS",
    "TRANSITIONS",
    "SandboxInstance",
    "SandboxLifecycleManager",
    "SandboxResourceQuota",
    "SandboxState",
    "can_transition",
    "get_sandbox_manager",
    "select_backend",
    "state_from_str",
]
