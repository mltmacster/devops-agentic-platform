#!/bin/bash
# VAULT TEST RUNNER
# Runs all tests with proper environment variables for SQLite backend

set -e

echo "============================================="
echo "  DAP FULL TEST SUITE"
echo "============================================="
echo ""

# Set test environment variables
export TESTING=1
export DATABASE_URL="sqlite+aiosqlite:///./dap_test.db"

# Run all tests
python -m pytest \
  --color=yes \
  --tb=short \
  tests/test_*.py \
  -v

echo ""
echo "============================================="
if [ $? -eq 0 ]; then
    echo "  ✅ ALL TESTS PASSED"
else
    echo "  ❌ SOME TESTS FAILED"
fi
