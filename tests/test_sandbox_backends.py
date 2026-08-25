"""Tests for the sandbox execution backends (null / podman / runsc).

No real container runtime required: the null backend is exercised end-to-end
through the manager; podman behavior is verified via argv construction and a
fake subprocess binary.
"""

import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

from src.sandbox_engine import (
    TIERS,
    NullBackend,
    PodmanBackend,
    SandboxLifecycleManager,
    SandboxState,
    select_backend,
)

from fake_backends import FakeStateBackend


# ─── Backend selection ─────────────────────────────

def test_null_backend_selection(monkeypatch):
    monkeypatch.setenv("DAP_SANDBOX_RUNTIME", "null")
    assert isinstance(select_backend(), NullBackend)


def test_forced_podman_falls_back_to_null_when_missing(monkeypatch):
    """Podman forced but absent on PATH (CI/Windows) → null, never crash."""
    monkeypatch.setenv("DAP_SANDBOX_RUNTIME", "podman")
    monkeypatch.setattr("src.sandbox_engine.backends.shutil.which", lambda *_: None)
    backend = select_backend()
    assert isinstance(backend, NullBackend)


def test_podman_selected_when_present(monkeypatch):
    monkeypatch.setenv("DAP_SANDBOX_RUNTIME", "podman")
    monkeypatch.setattr("src.sandbox_engine.backends.shutil.which", lambda name: "/usr/bin/podman")
    assert isinstance(select_backend(), PodmanBackend)


def test_runsc_selected_requires_both(monkeypatch):
    monkeypatch.setenv("DAP_SANDBOX_RUNTIME", "runsc")

    def which(name):
        return "/usr/bin/podman" if name == "podman" else None

    monkeypatch.setattr("src.sandbox_engine.backends.shutil.which", which)
    assert isinstance(select_backend(), NullBackend)  # no runsc → fall back


def test_auto_defaults_to_null_without_podman(monkeypatch):
    monkeypatch.delenv("DAP_SANDBOX_RUNTIME", raising=False)
    monkeypatch.setattr("src.sandbox_engine.backends.shutil.which", lambda *_: None)
    assert isinstance(select_backend(), NullBackend)


# ─── Podman argv construction ──────────────────────

def test_podman_create_argv_includes_limits_and_isolation(monkeypatch):
    backend = PodmanBackend(binary="/usr/bin/podman")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return type("P", (), {"returncode": 0, "stdout": "abc123\n", "stderr": ""})()

    monkeypatch.setattr("src.sandbox_engine.backends.subprocess.run", fake_run)
    container_id = backend.create("0123456789abcdef", "ubuntu:24.04", mem_gb=2, cpu=1.0)

    assert container_id == "abc123"
    cmd = captured["cmd"]
    assert cmd[0] == "/usr/bin/podman"
    assert "create" in cmd
    assert "--network" in cmd and "none" in cmd  # no external network by default
    assert "--memory" in cmd and "2048m" in cmd
    assert "--cpus" in cmd and "1.0" in cmd
    assert "--pull" in cmd and "missing" in cmd  # fresh host pulls the base image


def test_podman_runsc_flag():
    backend = PodmanBackend(binary="/usr/bin/podman", runsc=True)
    assert backend.name == "runsc"
    assert backend._base() == ["/usr/bin/podman", "--runtime", "runsc"]


def test_podman_nonzero_exit_reports_failure(monkeypatch):
    backend = PodmanBackend(binary="/usr/bin/podman")

    def fake_run(cmd, **kwargs):
        return type("P", (), {"returncode": 125, "stdout": "", "stderr": "no such container"})()

    monkeypatch.setattr("src.sandbox_engine.backends.subprocess.run", fake_run)
    assert backend.start("missing") is False


def test_podman_oserror_reports_failure(monkeypatch):
    backend = PodmanBackend(binary="/usr/bin/podman")

    def fake_run(cmd, **kwargs):
        raise OSError("podman not executable")

    monkeypatch.setattr("src.sandbox_engine.backends.subprocess.run", fake_run)
    assert backend.start("x") is False


# ─── Fake podman end-to-end through the manager ─────────────

@pytest.fixture()
def fake_podman(tmp_path, monkeypatch):
    """A fake `podman` executable that records commands and tracks container
    state exactly like real podman (created/running/exited/paused)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "podman_calls.log"
    state = tmp_path / "podman_state"

    script = bin_dir / "podman"
    # The kernel requires "#!" on the very first byte and LF endings: strip the
    # leading newline from the triple-quoted string and normalize CRLF (which
    # appears in Windows checkouts of this repo).
    script.write_text(
        textwrap.dedent(f"""
            #!/bin/sh
            STATE={state}
            case "$1" in
                create)  echo created > $STATE; echo fakecontainer123 ;;
                start)   echo running > $STATE ;;
                stop)    echo exited > $STATE ;;
                pause)   echo paused > $STATE ;;
                unpause) echo running > $STATE ;;
                rm)      rm -f $STATE ;;
                inspect) [ -f $STATE ] && cat $STATE ;;
            esac
            echo "$@" >> {log}
            exit 0
        """).replace("\r\n", "\n").lstrip("\n")
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    monkeypatch.setenv("DAP_SANDBOX_RUNTIME", "podman")
    monkeypatch.setattr("src.sandbox_engine.backends.shutil.which", lambda name: str(script))
    return log


@pytest.mark.skipif(sys.platform == "win32", reason="fake POSIX script; CI covers Linux")
def test_manager_with_fake_podman(fake_podman):
    manager = SandboxLifecycleManager()
    assert manager.runtime == "podman"

    sb = manager.create_sandbox(tier="basic")
    assert sb.status == SandboxState.CREATING
    assert sb.container_id == "fakecontainer123"

    # Running: suspend pauses the container, resume unpauses it.
    assert manager.start_sandbox(sb.id).status == SandboxState.RUNNING
    assert manager.suspend_sandbox(sb.id).status == SandboxState.SUSPENDED
    assert manager.resume_sandbox(sb.id).status == SandboxState.RUNNING

    # Stopped, then suspended: the container is already exited, so suspend is a
    # container no-op and resume must (re)START it — the real podman semantics.
    assert manager.stop_sandbox(sb.id).status == SandboxState.STOPPED
    assert manager.suspend_sandbox(sb.id).status == SandboxState.SUSPENDED
    assert manager.resume_sandbox(sb.id).status == SandboxState.RUNNING

    assert manager.delete_sandbox(sb.id) is None

    calls = fake_podman.read_text().splitlines()
    assert sum(1 for l in calls if l.startswith("create ")) == 1
    assert sum(1 for l in calls if l.startswith("start ")) == 2   # initial + re-start on resume
    assert sum(1 for l in calls if l.startswith("stop ")) == 1
    assert sum(1 for l in calls if l.startswith("pause ")) == 1   # only suspend-while-running
    assert sum(1 for l in calls if l.startswith("unpause ")) == 1
    assert sum(1 for l in calls if l.startswith("rm ")) == 1


def test_manager_backend_failure_parks_in_error(monkeypatch):
    class FailingBackend(NullBackend):
        name = "failing"

        def create(self, sandbox_id, image, mem_gb, cpu):
            return None  # simulate a failed podman create

        def start(self, container_id):
            return False  # every op on a containerless sandbox fails

    manager = SandboxLifecycleManager(backend=FailingBackend())
    sb = manager.create_sandbox()
    assert sb.status == SandboxState.ERROR
    assert sb.container_id is None

    # every op on a containerless sandbox fails and parks in ERROR
    assert manager.start_sandbox(sb.id).status == SandboxState.ERROR

    # ...but DELETE always cleans it up
    assert manager.delete_sandbox(sb.id) is None
    assert manager.get_sandbox(sb.id) is None


# ─── execute_op (stateless path used by the DB-backed API) ─────────


def test_execute_op_state_tolerance():
    """execute_op must apply podman's real state semantics (SOLUTION 36).

    Uses a state-tracking fake so this runs on every platform; the
    fake-podman end-to-end test above covers the same paths through a
    real (scripted) binary on Linux/CI.
    """
    backend = FakeStateBackend()
    manager = SandboxLifecycleManager(backend=backend)

    cid = backend.create("sb-12345678", "ubuntu:24.04", 2, 1)
    assert backend.state(cid) == "created"

    # created → running
    assert manager.execute_op("start", "sb1", cid) is True
    assert backend.state(cid) == "running"
    assert backend.count("start") == 1

    # running → exited
    assert manager.execute_op("stop", "sb1", cid) is True
    assert backend.state(cid) == "exited"

    # stop an already-exited container: no-op success, no backend stop call
    assert manager.execute_op("stop", "sb1", cid) is True
    assert backend.count("stop") == 1

    # suspend an exited container: bookkeeping only — real podman cannot
    # pause it, and the state-tolerant path must not try (SOLUTION 36)
    assert manager.execute_op("suspend", "sb1", cid) is True
    assert backend.count("pause") == 0
    assert backend.state(cid) == "exited"

    # resume an exited container: must (re)START it
    assert manager.execute_op("resume", "sb1", cid) is True
    assert backend.state(cid) == "running"
    assert backend.count("start") == 2

    # suspend a running container: real pause; resume unpauses
    assert manager.execute_op("suspend", "sb1", cid) is True
    assert backend.state(cid) == "paused"
    assert manager.execute_op("resume", "sb1", cid) is True
    assert backend.state(cid) == "running"
    assert backend.count("unpause") == 1

    # remove destroys the container
    assert manager.execute_op("remove", "sb1", cid) is True
    assert backend.state(cid) == ""


def test_execute_op_missing_container_parks_error():
    """A container that vanished from the host (e.g. host reset) fails the op."""
    backend = FakeStateBackend()
    manager = SandboxLifecycleManager(backend=backend)

    cid = backend.create("sb-87654321", "img", 1, 1)
    backend.start(cid)
    del backend.containers[cid]  # simulate `podman system reset` on the host

    assert manager.execute_op("start", "sbX", cid) is False


def test_execute_op_without_container():
    """Ops on a sandbox whose create failed (container_id=None) must fail,
    so the caller can park it in ERROR; remove is a clean no-op."""
    manager = SandboxLifecycleManager(backend=FakeStateBackend())

    assert manager.execute_op("remove", "sbX", None) is True
    for op in ("start", "stop", "suspend", "resume"):
        assert manager.execute_op(op, "sbX", None) is False

    with pytest.raises(ValueError):
        manager.execute_op("bogus", "sbX", None)


def test_create_sandbox_with_explicit_id():
    """The API passes its own (DB) id; the manager must honor it."""
    manager = SandboxLifecycleManager(backend=FakeStateBackend())
    sb = manager.create_sandbox(tier="basic", sandbox_id="my-external-id")
    assert sb.id == "my-external-id"
    assert sb.container_id == "cid-my-exter"  # first 8 chars of the id


def test_tiers_constant():
    """The API validates tiers against this map."""
    assert set(TIERS) == {"basic", "pro", "enterprise", "ga"}
    assert TIERS["basic"].cpu_cores == 1.0
    assert TIERS["basic"].memory_gb == 2.0


def test_null_backend_manager_lifecycle_unchanged():
    """The original in-memory behavior is preserved with the null backend."""
    manager = SandboxLifecycleManager(backend=NullBackend())
    assert manager.runtime == "null"

    sb = manager.create_sandbox(tier="pro")
    assert sb.status == SandboxState.CREATING
    assert sb.container_id  # sentinel id

    assert manager.start_sandbox(sb.id).status == SandboxState.RUNNING
    assert manager.stop_sandbox(sb.id).status == SandboxState.STOPPED
    assert manager.suspend_sandbox(sb.id).status == SandboxState.SUSPENDED
    assert manager.resume_sandbox(sb.id).status == SandboxState.RUNNING
    assert manager.delete_sandbox(sb.id) is None
    assert manager.get_sandbox(sb.id) is None
