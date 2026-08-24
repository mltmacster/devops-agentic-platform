"""Suite-wide test configuration.

The sandbox backend is auto-detected from the environment (DAP_SANDBOX_RUNTIME,
default: podman if on PATH, else in-memory). Test suites must be deterministic
in any environment — GitHub-hosted Linux runners ship a working podman, so
without this the manager would drive real containers instead of the in-memory
one the engine/API tests were written against. Force the in-memory backend
here; tests that need a specific backend construct it explicitly (or, for the
fake-podman end-to-end test, set DAP_SANDBOX_RUNTIME themselves).
"""
import os

os.environ.setdefault("DAP_SANDBOX_RUNTIME", "null")
