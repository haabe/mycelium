#!/usr/bin/env bash
# tests/bash/run.sh
# Discovery + execution for tests/bash/test_*.sh files.
# Invoked from tests/validate-template.sh Check 17 alongside pytest.
#
# Exit code: 0 if all tests pass, 1 if any test fails.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

total_pass=0
total_fail=0

for test_file in test_*.sh; do
    [ -f "$test_file" ] || continue
    if bash "$test_file"; then
        total_pass=$((total_pass + 1))
    else
        total_fail=$((total_fail + 1))
    fi
done

echo ""
echo "================================================="
echo "Bash check tests: $total_pass test files passed, $total_fail test files failed"
echo "================================================="

if [ "$total_fail" -gt 0 ]; then
    exit 1
fi
exit 0
