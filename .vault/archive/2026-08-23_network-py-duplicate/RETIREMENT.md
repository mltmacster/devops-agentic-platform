# Retired: src/network.py

- Retired: 2026-08-23 (health audit)
- Reason: Full duplicate of `src/network/url_formatter.py` (diff: whitespace/docstring only).
  The `src/network/` package shadows the module, so `src/network.py` was unreachable —
  a parallel source of truth that could drift and confuse future agents.
- Replacement: `src/network/url_formatter.py` (re-exported by `src/network/__init__.py`)
- Backup of the retired file: `network.py.bak` in this folder
- Migration: None required — `from src.network import ...` already resolved to the package.
