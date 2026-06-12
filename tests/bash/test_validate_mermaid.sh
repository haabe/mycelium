#!/usr/bin/env bash
# tests/bash/test_validate_mermaid.sh
# G-V12 coverage proof for scripts/validate_mermaid.py — the render-fleet static
# validator that closes the agent-blind-spot (F11 state-id consistency, F13 WCAG
# contrast). Every check ships with a known-bad case it catches + a known-good
# case it passes.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VALIDATOR="$REPO_ROOT/plugins/mycelium/scripts/validate_mermaid.py"

test_flags_contrast_failure() {
    # Yellow label on white background — 1.07:1, far below 4.5:1 AA.
    local diagram output rc
    diagram='stateDiagram-v2
  %%{init: {"themeVariables": {"cScale0": "#FFFFFF", "cScaleLabel0": "#FFFF00"}}}%%'
    output=$(printf '%s\n' "$diagram" | python3 "$VALIDATOR" - 2>&1); rc=$?
    assert_contains "$output" "FAIL: contrast" "flags sub-AA contrast pair"
    assert_eq "$rc" "1" "exits 1 on contrast failure"
}

test_flags_undeclared_state_id() {
    # L1 referenced in a transition but never declared.
    local diagram output rc
    diagram='stateDiagram-v2
  state "Purpose" as L0
  L0 --> L1'
    output=$(printf '%s\n' "$diagram" | python3 "$VALIDATOR" - 2>&1); rc=$?
    assert_contains "$output" "FAIL: state-id 'L1'" "flags undeclared state id"
    assert_eq "$rc" "1" "exits 1 on undeclared state id"
}

test_passes_documented_palette() {
    # The actual render-conventions.md palette — all pairs claim >4.5:1 AA.
    local diagram output rc
    diagram='stateDiagram-v2
  %%{init: {"themeVariables": {"cScale4": "#AB47BC", "cScaleLabel4": "#FFFFFF", "git0": "#FDD835", "gitBranchLabel0": "#000000"}}}%%'
    output=$(printf '%s\n' "$diagram" | python3 "$VALIDATOR" - 2>&1); rc=$?
    assert_not_contains "$output" "FAIL" "no false positive on documented palette"
    assert_eq "$rc" "0" "exits 0 on the documented palette"
}

test_passes_clean_declared_diagram() {
    local diagram output rc
    diagram='stateDiagram-v2
  state "Purpose" as L0
  state "Strategy" as L1
  L0 --> L1
  L1 --> [*]'
    output=$(printf '%s\n' "$diagram" | python3 "$VALIDATOR" - 2>&1); rc=$?
    assert_not_contains "$output" "FAIL" "clean declared diagram passes"
    assert_eq "$rc" "0" "exits 0 on clean diagram"
}

echo "=== test_validate_mermaid: render-fleet static validator (F11 + F13) ==="
run_test test_flags_contrast_failure
run_test test_flags_undeclared_state_id
run_test test_passes_documented_palette
run_test test_passes_clean_declared_diagram
report
