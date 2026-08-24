# =============================================
# 🏛️ PROJECT VAULT — DO NOT MODIFY BY AGENTS
# =============================================

**WARNING:** This directory is the project's official knowledge repository.
Agents and automation systems MUST NOT:
- Delete files in this directory
- Remove or modify existing entries without explicit human approval
- Auto-purge old content

This vault is maintained for:
1. **UI/UX Preview** — Screenshots, dashboard exports, code snapshots
2. **Debugging Solutions** — Documented troubleshooting with root cause analysis  
3. **Architecture History** — Design decisions, ADRs, Mermaid diagrams
4. **Script Library** — Reusable automation and debugging scripts
5. **Deprecated Components** — Retirement documentation with migration paths

---

## 📁 Directory Structure

```
.vault/
├── VAULT_CONFIG.yaml           # Schema definitions (READ-ONLY)
├── VAULT_COORDINATOR.yaml      # Cross-cutting coordination rules (READ-ONLY)
├── LIFECYCLE_PROTOCOL.md       # Artifact lifecycle rules (READ-ONLY)
├── ARCHITECTURE.md             # Current architecture state
├── ARCHITECTURE.md.bak         # Previous architecture state
├── SNAPSHOT_LOG.md             # Snapshot tracking
└── .../                        # Artifact-specific directories
```

---

## 🔄 How to Add Artifacts

### 1. Code Snapshot (After Major Changes)
```yaml
# .vault/snapshots/YYYY-MM-DD-HH/MM/<service>/snap_<feature>.md
- Description: [what changed]
- Files Changed: [list paths]
- Key Diff Points: [bullet points]
```

### 2. Design Document (Architecture Change)  
```markdown
# .vault/designs/YYYY-MM-DD_<feature>.md

## Decision ID: ADR-XXX
### Problem: [what problem]
### Solution: [what we chose]
### Alternatives Considered: [what we rejected & why]
```

### 3. Troubleshooting Solution  
```markdown
# .vault/docs/solutions/YYYY-MM-DD_ISSUE.md

## Issue: [what broke]
## Root Cause: [why it broke]  
## Solution: [how to fix it]
## Verification Steps:
1. [step 1]
2. [step 2]
```

### 4. Deprecated Component
```markdown
# .vault/archive/YYYY-MM-DD_<component>/RETIREMENT.md

## Component: <name>
## Retired: <date>
## Reason: <why it was replaced>

### Migration Steps:
1. [step 1]
2. [step 2]

### Old Code Location: <path>
### New Code Location: <path>
```

---

## 📋 Current Architecture State

### Services Implemented:
- ✅ Auth Service (RBAC, JWT) — **13 tests passing**
- ✅ Workspace Orchestrator — **11 tests passing**  
- ✅ Sandbox Lifecycle Manager — **11 tests passing**

### Pending:
- IDE WebSocket server (Monaco Editor integration)
- Observability metrics collector (Prometheus)
- Dashboard API (Grafana connection)
