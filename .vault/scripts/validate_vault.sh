#!/bin/bash
# VAULT VALIDATION SCRIPT
# Validates Vault YAML configurations and structure

set -e

VAULT_DIR="$(cd "$(dirname "$0")/.." && pwd)/.vault"
SCRIPT_DIR="$VAULT_DIR"

echo "============================================="
echo "  VAULT CONFIGURATION VALIDATOR"
echo "============================================="

# Check required YAML files exist
REQUIRED_FILES=(
  ".vault/VAULT_CONFIG.yaml"
  ".vault/VAULT_COORDINATOR.yaml"
  ".vault/LIFECYCLE_PROTOCOL.md"
)

errors=0

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ MISSING: $file"
        errors=$((errors + 1))
    else
        echo "✅ FOUND: $file"
    fi
done

# Validate YAML syntax
echo ""
echo "Checking YAML syntax..."
for yaml_file in .vault/*.yaml; do
    if [ -f "$yaml_file" ]; then
        echo "  Validating $(basename $yaml_file)..."
        python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" 2>/dev/null && \
            echo "  ✅ $yaml_file - Valid YAML" || \
            (echo "  ❌ $yaml_file - Invalid YAML" && errors=$((errors + 1)))
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
