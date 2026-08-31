#!/usr/bin/env bash
# tests/bash/test_validate_canvas_diamonds.sh
# G-V12 coverage proof for validate_canvas.py diamonds-dir validation (2026-06-12).
#
# Closes the coverage gap where .claude/diamonds/active.yml — the framework's
# most-read state file — was outside the validator's canvas glob and had no
# schema. Witnessed failure: the dogfood repo's active.yml sat
# committed-unparseable for >=3 days (unescaped interior double-quotes in a
# notes: scalar) with zero detection; every hook reading it silently degraded
# to defaults (roadmap corrections.md 2026-06-12). The broken_diamond fixture
# reproduces that exact defect shape.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures/validate_canvas_diamonds"
VALIDATOR="$REPO_ROOT/plugins/mycelium/scripts/validate_canvas.py"

# RESOLVE AN INTERPRETER THAT CAN ACTUALLY RUN THE VALIDATOR, AND SKIP HONESTLY IF NONE CAN.
#
# These tests asserted validator BEHAVIOUR while invoking a bare `python3`. Measured
# 2026-08-31: a background `mise` upgrade replaced Python 3.12 with 3.14.7 and deleted the
# old install, so `python3` lost `jsonschema`. validate_canvas.py then exited 2 with
# "jsonschema not installed", and these tests reported "needle 'YAML parse error' not found"
# — an ENVIRONMENT problem wearing the costume of a broken validator, which sends the reader
# hunting for a defect that does not exist.
#
# requirements-ci.txt states the intended split: hooks are stdlib-only, CI deps come from
# `uv run --with-requirements`. So prefer a python3 that already has them, else uv, else SKIP
# with the reason said out loud. A skipped test that names why is honest; a failing one here
# is a lie about the code.
PYV=""
if python3 -c "import jsonschema" >/dev/null 2>&1; then
    PYV="python3"
elif command -v uv >/dev/null 2>&1 && [ -f "$REPO_ROOT/requirements-ci.txt" ]; then
    PYV="uv run --quiet --with-requirements $REPO_ROOT/requirements-ci.txt python"
else
    echo "SKIP: $(basename "${BASH_SOURCE[0]}") — no interpreter can import jsonschema, so the" >&2
    echo "  validator cannot run. This is NOT a validator failure and NOT a pass: nothing was" >&2
    echo "  checked. Install the CI deps, or make uv available." >&2
    exit 0
fi


test_fails_loud_on_broken_diamond_yaml() {
    # The historical defect: notes: "... "interior quote" ..." stops the parse.
    local output rc
    output=$($PYV "$VALIDATOR" "$FIXTURES_DIR/broken_diamond/canvas" 2>&1); rc=$?
    assert_contains "$output" "YAML parse error in diamonds/active.yml" "names the failing diamonds file"
    assert_eq "$rc" "1" "exits 1 on broken diamonds YAML"
}

test_flags_schema_violations_in_diamond() {
    # Bad scale enum, out-of-range confidence, DoD missing required signal.
    local output rc
    output=$($PYV "$VALIDATOR" "$FIXTURES_DIR/bad_dod/canvas" 2>&1); rc=$?
    assert_contains "$output" "'L9' is not one of" "flags invalid scale enum"
    assert_contains "$output" "greater than the maximum of 1.0" "flags out-of-range confidence"
    assert_contains "$output" "'signal' is a required property" "flags DoD missing signal"
    assert_eq "$rc" "1" "exits 1 on diamond schema violations"
}

test_passes_clean_diamond() {
    local output rc
    output=$($PYV "$VALIDATOR" "$FIXTURES_DIR/clean/canvas" 2>&1); rc=$?
    assert_contains "$output" "Canvas validation: PASS" "clean diamond passes"
    assert_not_contains "$output" "diamonds/active.yml ::" "no diamond errors on clean fixture"
    assert_eq "$rc" "0" "exits 0 on clean fixture"
}

echo "=== test_validate_canvas_diamonds: diamonds-dir parse + schema coverage ==="
run_test test_fails_loud_on_broken_diamond_yaml
run_test test_flags_schema_violations_in_diamond
run_test test_passes_clean_diamond
report
