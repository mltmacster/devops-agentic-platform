# RETIREMENT — VAULT_DEPLOYMENT.yaml v1.0

**Component**: `.vault/VAULT_DEPLOYMENT.yaml` (v1.0, created 2026-08-21)
**Retired**: 2026-08-24 (user-approved)
**Replacement**: `.vault/VAULT_DEPLOYMENT.yaml` v2.0.0 (new file at vault root)
**Old file location**: `.vault/archive/2026-08-24_vault-deployment-v1/VAULT_DEPLOYMENT.yaml` (this directory)
**Pre-change snapshot**: `.vault/snapshots/2026-08-24-production/vault/VAULT_DEPLOYMENT.yaml` (byte-identical copy; verified with diff)

## Reason for retirement

Two defects, both confirmed during the 2026-08-24 vault consistency audit:

1. **Invalid YAML.** The `roadmap` section embeds markdown task-list checkboxes inside
   YAML list items (`- [ ] Implement IDE WebSocket server` followed by mis-indented
   `status:` / `files_needed:` / `dependencies:` keys). PyYAML rejects this:
   `- [ ] ...` is parsed as an empty flow sequence, and the indented keys after a
   scalar-valued `phase_2:` line are a mapping-in-block-context error. The file
   fails `yaml.safe_load`, which also defeats the validation loop in
   `scripts/validate_vault.sh` until fixed. The same checkbox pattern appears in
   `weekly_review`.
2. **Stale roadmap.** The plan was frozen at 2026-08-21 ("Phase 1 current") with
   Phases 2/3/4 all marked planning/not_started — while Phase 2 (IDE + observability),
   Phase 3 (agentic engine), and Phase 5 (networkability) are in fact COMPLETE, and
   the file lists none of the production-ready work that has since landed
   (compose stack, Caddy/TLS, real auth persistence, LLM metrics).

## Root cause

Roadmap checkboxes were written as markdown inside a YAML file — a format-boundary
violation. YAML is for machine-readable structure; open-ended checklists belong in
markdown or in a structured `status:` field. The file was never validated with
`yaml.safe_load` after being written, so the syntax error persisted for 3 days and
the staleness went unnoticed until the audit.

## Mitigation for the next build

- Checklists live in markdown (`.md`); YAML keeps only structured fields
  (names, statuses, dependencies) — enforced by habit, checked by validation.
- Every vault YAML is validated with `yaml.safe_load` before commit (the fixed
  `validate_vault.sh` does this for all `.vault/*.yaml`).
- `validate_vault.sh` now lists `VAULT_DEPLOYMENT.yaml` in REQUIRED_FILES, so a
  missing or unparseable roadmap fails validation loudly instead of silently.
- Roadmap updates happen in the same commit that completes a phase, so the plan
  can never drift more than one session.

## Migration steps

1. `mkdir .vault/archive/2026-08-24_vault-deployment-v1/`
2. `mv .vault/VAULT_DEPLOYMENT.yaml` into that directory (moved, not deleted)
3. Add this RETIREMENT.md
4. Write the new v2.0.0 `.vault/VAULT_DEPLOYMENT.yaml` (valid YAML, current state)
5. Run `bash .vault/scripts/validate_vault.sh` → all YAML valid

## Verification (2026-08-24)

- `python -c "import yaml; yaml.safe_load(open('.vault/VAULT_DEPLOYMENT.yaml'))"` → OK (v2)
- Archived v1 fails `yaml.safe_load` (expected — it is the buggy original, preserved as-is)
- `bash .vault/scripts/validate_vault.sh` → validation passed

## Documented in

`.vault/SOLUTIONS.md` — Solution 28 (vault consistency pass)
