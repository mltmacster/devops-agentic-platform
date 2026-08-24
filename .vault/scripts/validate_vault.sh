#!/bin/bash
# VAULT VALIDATION SCRIPT (v1.1 — 2026-08-24 consistency pass, user-approved)
# Validates Vault YAML configurations and structure.
# Fixes: VAULT_DIR no longer resolves to .vault/.vault (the script already
# lives inside .vault/scripts/); interpreter is auto-detected (python, with
# python3 fallback) since the MS Store python3 stub is broken on this machine;
# VAULT_DEPLOYMENT.yaml is now in REQUIRED_FILES.
# Run from the repo root: bash .vault/scripts/validate_vault.sh

# Resolve project root = parent of .vault (this script is in .vault/scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VAULT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$VAULT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

# Interpreter auto-detect: prefer `python`, fall back to `python3`
if command -v python >/dev/null 2>&1; then
    PY="python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "❌ No python interpreter found on PATH" >&2
    exit 1
fi

set -e

echo "============================================="
echo "  VAULT CONFIGURATION VALIDATOR"
echo "  Vault: $VAULT_DIR"
echo "============================================="

errors=0

# Check required vault files exist
REQUIRED_FILES=(
  ".vault/VAULT_CONFIG.yaml"
  ".vault/VAULT_COORDINATOR.yaml"
  ".vault/VAULT_DEPLOYMENT.yaml"
  ".vault/LIFECYCLE_PROTOCOL.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ MISSING: $file"
        errors=$((errors + 1))
    else
        echo "✅ FOUND: $file"
    fi
done

# Validate YAML syntax (PyYAML must be available in the chosen interpreter)
echo ""
echo "Checking YAML syntax..."
for yaml_file in .vault/*.yaml; do
    if [ -f "$yaml_file" ]; then
        echo "  Validating $(basename "$yaml_file")..."
        if "$PY" -c "import yaml, sys; yaml.safe_load(open(sys.argv[1], encoding='utf-8'))" "$yaml_file" 2>/dev/null; then
            echo "  ✅ $yaml_file - Valid YAML"
        else
            echo "  ❌ $yaml_file - Invalid YAML"
            errors=$((errors + 1))
        fi
    fi
done

# Check directory structure
echo ""
echo "Checking directory structure..."
for dir in archive snapshots designs scripts docs metrics; do
    if [ -d ".vault/$dir" ]; then
        echo "  ✅ .vault/$dir/ exists"
    else
        echo "  ⚠️  .vault/$dir/ missing (optional)"
    fi
done

echo ""
if [ $errors -eq 0 ]; then
    echo "============================================="
    echo "  ✅ VAULT VALIDATION PASSED"
    echo "============================================="
else
    echo ""
    echo "❌ Validation failed with $errors errors"
    exit 1
fi
