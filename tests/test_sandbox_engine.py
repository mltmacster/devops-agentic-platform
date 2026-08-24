"""Tests for the Sandbox Engine — lifecycle state machine and VM manager.

Pure unit tests (no database): verifies the TRANSITIONS state machine and
the in-memory SandboxLifecycleManager behavior.
"""

import pytest

from src.sandbox_engine import (
    TRANSITIONS,
    SandboxLifecycleManager,
    SandboxState,
    can_transition,
    get_sandbox_manager,
    state_from_str,
)


# ─── State Machine ──────────────

@pytest.mark.parametrize(
    "current,target",
    [
        (SandboxState.CREATING, SandboxState.RUNNING),
        (SandboxState.CREATING, SandboxState.STOPPED),
        (SandboxState.CREATING, SandboxState.SUSPENDED),
        (SandboxState.CREATING, SandboxState.ERROR),
        (SandboxState.CREATING, SandboxState.DELETED),
        (SandboxState.RUNNING, SandboxState.STOPPED),
        (SandboxState.RUNNING, SandboxState.SUSPENDED),
        (SandboxState.RUNNING, SandboxState.ERROR),
        (SandboxState.RUNNING, SandboxState.DELETED),
        (SandboxState.STOPPED, SandboxState.RUNNING),
        (SandboxState.STOPPED, SandboxState.SUSPENDED),
        (SandboxState.STOPPED, SandboxState.DELETED),
        (SandboxState.SUSPENDED, SandboxState.RUNNING),
        (SandboxState.SUSPENDED, SandboxState.STOPPED),
        (SandboxState.SUSPENDED, SandboxState.DELETED),
        (SandboxState.ERROR, SandboxState.RUNNING),
        (SandboxState.ERROR, SandboxState.DELETED),
    ],
)
def test_legal_transitions(current, target):
    assert can_transition(current, target) is True


@pytest.mark.parametrize(
    "current,target",
    [
        (SandboxState.RUNNING, SandboxState.RUNNING),   # self
        (SandboxState.STOPPED, SandboxState.STOPPED),   # self
        (SandboxState.DELETED, SandboxState.RUNNING),   # terminal
        (SandboxState.DELETED, SandboxState.DELETED),   # terminal self
        (SandboxState.RUNNING, SandboxState.CREATING),  # no backwards to creating
        (SandboxState.ERROR, SandboxState.SUSPENDED),
        (SandboxState.ERROR, SandboxState.STOPPED),
    ],
)
def test_illegal_transitions(current, target):
    assert can_transition(current, target) is False


def test_every_state_has_entry():
    assert set(TRANSITIONS) == set(SandboxState)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("running", SandboxState.RUNNING),
        ("STOPPED", SandboxState.STOPPED),
        ("creating", SandboxState.CREATING),
        ("suspended", SandboxState.SUSPENDED),
        ("error", SandboxState.ERROR),
        ("deleted", SandboxState.DELETED),
    ],
)
def test_state_from_str_valid(value, expected):
    assert state_from_str(value) == expected


def test_state_from_str_invalid():
    assert state_from_str("not-a-state") is None
    assert state_from_str("") is None


# ─── In-Memory Manager ──────────────

def test_create_and_get():
    manager = get_sandbox_manager()
    instance = manager.create_sandbox(tier="pro")

    assert instance.status == SandboxState.CREATING
    assert instance.resources.cpu_cores == 4.0
    assert manager.get_sandbox(instance.id) is instance
    assert len(manager.list_sandboxes()) == 1


def test_full_lifecycle_flow():
    manager = get_sandbox_manager()
    sb = manager.create_sandbox()
    sb_id = sb.id

    assert manager.start_sandbox(sb_id).status == SandboxState.RUNNING
    assert manager.stop_sandbox(sb_id).status == SandboxState.STOPPED
    assert manager.suspend_sandbox(sb_id).status == SandboxState.SUSPENDED
    assert manager.resume_sandbox(sb_id).status == SandboxState.RUNNING
    assert manager.delete_sandbox(sb_id) is None
    assert manager.get_sandbox(sb_id) is None


def test_delete_running_allowed():
    """DELETE is terminal-destroying: legal from any non-deleted state."""
    manager = get_sandbox_manager()
    sb = manager.create_sandbox()
    manager.start_sandbox(sb.id)

    assert manager.delete_sandbox(sb.id) is None
    assert manager.get_sandbox(sb.id) is None


def test_illegal_transitions_noop():
    manager = get_sandbox_manager()
    sb = manager.create_sandbox()
    manager.start_sandbox(sb.id)

    # Running sandbox cannot be started again
    assert manager.start_sandbox(sb.id) is None
    assert manager.get_sandbox(sb.id).status == SandboxState.RUNNING


def test_unknown_id_returns_none():
    manager = get_sandbox_manager()
    assert manager.start_sandbox("nope") is None
    assert manager.stop_sandbox("nope") is None
    assert manager.suspend_sandbox("nope") is None
    assert manager.resume_sandbox("nope") is None
    assert manager.delete_sandbox("nope") is None


def test_usage_stats():
    manager = get_sandbox_manager()
    a = manager.create_sandbox()
    b = manager.create_sandbox()
    manager.start_sandbox(a.id)
    manager.stop_sandbox(b.id)

    stats = manager.get_sandbox_usage_stats()
    assert stats["total"] == 2
    assert stats["running"] == 1
    assert stats["stopped"] == 1


def test_list_filter_by_status():
    manager = get_sandbox_manager()
    a = manager.create_sandbox()
    b = manager.create_sandbox()
    manager.start_sandbox(a.id)

    assert manager.list_sandboxes(status=SandboxState.RUNNING) == [a]
    assert manager.list_sandboxes(status=SandboxState.CREATING) == [b]
