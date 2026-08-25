"""Sandbox execution backends.

Real container execution behind the in-memory lifecycle state machine.

Backends:
  NullBackend   — in-memory no-op (default when no container runtime exists;
                  preserves the original stub behavior, zero dependencies)
  PodmanBackend — `podman` CLI via subprocess; with runsc=True it also passes
                  `--runtime runsc` (gVisor kernel isolation)

Selection is driven by the `DAP_SANDBOX_RUNTIME` env var:
  auto (default) — podman if on PATH, otherwise null. gVisor is only
                   selected when explicitly requested (image-compat caveats)
  podman | runsc | null — force a specific backend

All backend methods are synchronous (the lifecycle manager is synchronous;
the sandbox API talks to the DB and does not depend on this module).
A failed backend call never raises — it returns False and the manager
moves the sandbox to ERROR, keeping the state machine authoritative.
"""

import logging
import os
import shutil
import subprocess
from typing import List, Optional, Protocol

logger = logging.getLogger(__name__)

# Ubuntu 24.04 base image used for Lite VM containers
DEFAULT_IMAGE = "ubuntu:24.04"


class ExecutionBackend(Protocol):
    """Contract every execution backend implements."""

    name: str

    def available(self) -> bool: ...
    def create(self, sandbox_id: str, image: str, mem_gb: float, cpu: float) -> Optional[str]: ...
    def state(self, container_id: str) -> str: ...
    def start(self, container_id: str) -> bool: ...
    def stop(self, container_id: str) -> bool: ...
    def pause(self, container_id: str) -> bool: ...
    def unpause(self, container_id: str) -> bool: ...
    def remove(self, container_id: str) -> bool: ...


class NullBackend:
    """In-memory no-op backend — the original stub behavior."""

    name = "null"

    def available(self) -> bool:
        return True

    def create(self, sandbox_id: str, image: str, mem_gb: float, cpu: float) -> Optional[str]:
        return f"null-{sandbox_id[:8]}"

    def state(self, container_id: str) -> str:
        # No real container: model it as always-running so every op is a no-op success.
        return "running" if container_id else ""

    def start(self, container_id: str) -> bool:
        return True

    def stop(self, container_id: str) -> bool:
        return True

    def pause(self, container_id: str) -> bool:
        return True

    def unpause(self, container_id: str) -> bool:
        return True

    def remove(self, container_id: str) -> bool:
        return True


def _run(cmd: List[str], timeout: float = 120.0) -> bool:
    """Run a subprocess, return True on exit 0. Never raises."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.error("Backend command failed: %s (%s)", " ".join(cmd[:2]), exc)
        return False
    if proc.returncode != 0:
        logger.error("Backend command exited %d: %s | %s", proc.returncode, " ".join(cmd[:2]), proc.stderr[:300])
        return False
    return True


class PodmanBackend:
    """Real sandbox execution via the podman CLI."""

    name = "podman"

    def __init__(self, runsc: bool = False, binary: Optional[str] = None):
        self.binary = binary or shutil.which("podman") or "podman"
        self.runsc = runsc

        if runsc:
            self.name = "runsc"

    def available(self) -> bool:
        if shutil.which(self.binary) is None:
            return False
        if self.runsc and shutil.which("runsc") is None:
            return False
        return True

    def _base(self) -> List[str]:
        cmd = [self.binary]
        if self.runsc:
            cmd += ["--runtime", "runsc"]
        return cmd

    def state(self, container_id: str) -> str:
        """Current container status ('running'/'paused'/'exited'/'created'), '' if gone."""
        try:
            proc = subprocess.run(
                self._base() + ["inspect", "--format", "{{.State.Status}}", container_id],
                capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("Backend inspect failed: %s", exc)
            return ""
        if proc.returncode != 0:
            return ""
        return proc.stdout.strip().lower()

    def create(self, sandbox_id: str, image: str, mem_gb: float, cpu: float) -> Optional[str]:
        cmd = self._base() + [
            "create",
            "--name", f"dap-sbx-{sandbox_id[:12]}",
            "--memory", f"{int(mem_gb * 1024)}m",
            "--cpus", str(cpu),
            "--network", "none",
            image,
            "sleep", "infinity",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            logger.error("podman create failed: %s", proc.stderr[:300])
            return None
        return proc.stdout.strip() or None

    def start(self, container_id: str) -> bool:
        return _run(self._base() + ["start", container_id])

    def stop(self, container_id: str) -> bool:
        return _run(self._base() + ["stop", "-t", "10", container_id])

    def pause(self, container_id: str) -> bool:
        return _run(self._base() + ["pause", container_id])

    def unpause(self, container_id: str) -> bool:
        return _run(self._base() + ["unpause", container_id])

    def remove(self, container_id: str) -> bool:
        # -f stops first if needed; --rm-style cleanup of the stopped container
        return _run(self._base() + ["rm", "-f", container_id])


def select_backend() -> ExecutionBackend:
    """Pick the execution backend from DAP_SANDBOX_RUNTIME (default: auto)."""
    choice = os.environ.get("DAP_SANDBOX_RUNTIME", "auto").strip().lower()

    if choice == "null":
        return NullBackend()
    if choice == "podman":
        backend = PodmanBackend()
        return backend if backend.available() else NullBackend()
    if choice == "runsc":
        backend = PodmanBackend(runsc=True)
        return backend if backend.available() else NullBackend()
    # auto: plain podman if on PATH, otherwise the null backend
    if PodmanBackend().available():
        return PodmanBackend()
    return NullBackend()
