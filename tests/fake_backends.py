"""Shared fake execution backends for tests.

FakeStateBackend emulates a real container runtime (podman) with the same
success/failure semantics for lifecycle ops — including the rules that
caused SOLUTION 36 (real podman cannot `pause` an exited container, cannot
`start` a running one, and every op on a missing container exits 125). It
records every call so tests can assert exact op sequences, and it runs on
any platform (no binary, no container runtime required).
"""


class FakeStateBackend:
    """In-memory fake with real podman-style state semantics.

    Container states: created → running → (paused ↔ running) → exited.
    """

    name = "fake-state"

    def __init__(self):
        self.containers: dict[str, str] = {}
        self.calls: list[str] = []

    # ── helpers ─────────────────────────────────────────────

    def _allowed(self, op: str, container_id: str) -> bool:
        """Would real podman accept `op` given the container's current state?"""
        if op == "remove":
            return True  # rm -f is idempotent
        if container_id not in self.containers:
            return False  # "no such container" (exit 125)
        st = self.containers[container_id]
        table = {
            "start": ("created", "exited"),
            "stop": ("running", "paused"),
            "pause": ("running",),  # SOLUTION 36: pause of exited/created fails
            "unpause": ("paused",),
        }
        return st in table[op]

    # ── ExecutionBackend protocol ───────────────────────────

    def available(self) -> bool:
        return True

    def create(self, sandbox_id: str, image: str, mem_gb: float, cpu: float) -> str:
        cid = f"cid-{sandbox_id[:8]}"
        self.containers[cid] = "created"
        self.calls.append("create")
        return cid

    def state(self, container_id: str) -> str:
        return self.containers.get(container_id, "")

    def start(self, container_id: str) -> bool:
        self.calls.append("start")
        if not self._allowed("start", container_id):
            return False
        self.containers[container_id] = "running"
        return True

    def stop(self, container_id: str) -> bool:
        self.calls.append("stop")
        if not self._allowed("stop", container_id):
            return False
        self.containers[container_id] = "exited"
        return True

    def pause(self, container_id: str) -> bool:
        self.calls.append("pause")
        if not self._allowed("pause", container_id):
            return False
        self.containers[container_id] = "paused"
        return True

    def unpause(self, container_id: str) -> bool:
        self.calls.append("unpause")
        if not self._allowed("unpause", container_id):
            return False
        self.containers[container_id] = "running"
        return True

    def remove(self, container_id: str) -> bool:
        self.calls.append("remove")
        self.containers.pop(container_id, None)
        return True

    # ── test assertions ─────────────────────────────────────

    def count(self, op: str) -> int:
        """Number of times a backend op (not state()) was invoked."""
        return sum(1 for c in self.calls if c == op)
