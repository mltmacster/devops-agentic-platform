# Retired: Dead Agentic/Observability Modules (2026-08-23)

Archived during the full framework/codebase audit. Neither file was imported by
any module, service, or test. Both failed to import at all.

## `metrics_collector.py` (was `src/api/observability/metrics_collector.py`)

- **Why retired**: SyntaxError — f-strings on the `sandbox_*` metric lines use
  `{{...}}` without the closing `}}`, so the module could never be imported
  (`f-string: single '}' is not allowed`).
- **Live replacement**: `src/api/observability/main.py` owns all metrics
  collection/export (`/api/observability/metrics` + summary + Grafana APIs).
- **Migration path**: none needed — nothing referenced this file. If per-sandbox
  metric rendering is ever wanted, rewrite against the live collector.

## `plugin_registry.py` (was `src/agentic/plugin_registry.py`)

- **Why retired**: NameError on import — uses `@abstractmethod` and `Any`
  without importing them. It also re-declared its own `BasePlugin`/`BaseAgent`
  classes, duplicating the real bases.
- **Live replacements**:
  - `src/agentic/plugin_interface.py` — `BaseAgent` (used by all three agents)
  - `src/agentic/common/plugin_interface.py` — `BasePlugin` + `StackModule`
    (used by `src/api/sandbox/stacks.py`) + its own `PluginRegistry`
- **Migration path**: nothing references the archived registry; no action.

## Verification

- `TESTING=1 python -m pytest tests/ -q` → 118/118 passing after archival.
- Import sweep of all 23 live `src.*` modules → all import cleanly.
