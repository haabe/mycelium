#!/usr/bin/env bash
# tests/bash/test_hook_fire_log.sh — the shared hook fire-logger.
#
# WHY THESE ASSERTIONS AND NOT OTHERS. The helper's contract has three clauses and only one of
# them is about writing a row:
#   1. It records a fire in a form `check_retirement_candidates.py` can read.
#   2. It names the CALLING hook, not itself — otherwise every row says `_hook_fire_log.sh`
#      and the per-hook question the check asks cannot be answered.
#   3. **It never changes the caller's verdict.** A gate that started failing because a disk was
#      full would be a far worse defect than a missing row, so every failure path returns 0.
# Clause 3 was hand-verified when the helper shipped (v0.234.0) and not pinned; a claim verified
# once and never asserted is the gap this file closes.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HELPER="$REPO_ROOT/plugins/mycelium/scripts/_hook_fire_log.sh"

# Run the helper from a throwaway hook script, so BASH_SOURCE[1] is a real caller.
run_from_fake_hook() {  # $1 hook filename, $2 project dir, $3.. args to mycelium_log_fire
    local hook_name="$1" proj="$2"; shift 2
    cat > "$proj/$hook_name" <<EOF
#!/usr/bin/env bash
. "$HELPER"
mycelium_log_fire $*
echo "rc=\$?"
EOF
    PROJECT_DIR="$proj" bash "$proj/$hook_name" 2>&1
}

test_writes_a_row_a_consumer_can_read() {
    local tmp; tmp=$(mktemp -d)
    run_from_fake_hook "fake-gate.sh" "$tmp" '".claude/state/fake-gate-fires.jsonl" "blocked" "src/x.py"' >/dev/null
    local row; row=$(cat "$tmp/.claude/state/fake-gate-fires.jsonl" 2>/dev/null)
    assert_contains "$row" '"outcome": "blocked"' "records the outcome"
    assert_contains "$row" '"detail": "src/x.py"' "records the detail label"
    assert_contains "$row" '"ts":' "stamps a timestamp"
    rm -rf "$tmp"
}

test_names_the_calling_hook_not_the_helper() {
    # If this regresses, every row reads `_hook_fire_log.sh` and the per-hook
    # question check_retirement_candidates asks becomes unanswerable.
    local tmp; tmp=$(mktemp -d)
    run_from_fake_hook "discovery-gate.sh" "$tmp" '".claude/state/d.jsonl" "blocked"' >/dev/null
    local row; row=$(cat "$tmp/.claude/state/d.jsonl" 2>/dev/null)
    assert_contains "$row" '"hook": "discovery-gate.sh"' "names the caller"
    assert_not_contains "$row" "_hook_fire_log" "does not name itself"
    rm -rf "$tmp"
}

test_returns_zero_when_the_log_cannot_be_written() {
    # THE CLAUSE THAT MATTERS. A gate must not start failing because logging did.
    local tmp; tmp=$(mktemp -d)
    cat > "$tmp/h.sh" <<EOF
#!/usr/bin/env bash
. "$HELPER"
mycelium_log_fire ".claude/state/x.jsonl" "blocked"
echo "rc=\$?"
EOF
    local out; out=$(PROJECT_DIR="/nonexistent-path-$$-xyz" bash "$tmp/h.sh" 2>&1)
    assert_contains "$out" "rc=0" "unwritable target still returns 0"
    rm -rf "$tmp"
}

test_empty_path_is_a_noop_not_an_error() {
    local tmp; tmp=$(mktemp -d)
    cat > "$tmp/h.sh" <<EOF
#!/usr/bin/env bash
. "$HELPER"
mycelium_log_fire "" "blocked"
echo "rc=\$?"
EOF
    local out; out=$(PROJECT_DIR="$tmp" bash "$tmp/h.sh" 2>&1)
    assert_contains "$out" "rc=0" "missing path returns 0 rather than erroring"
    rm -rf "$tmp"
}

test_detail_is_truncated_because_it_is_a_label_not_a_transcript() {
    # The privacy rule (DL-1262) is that a row carries a label, never content.
    # Truncation is the mechanical half of that promise.
    local tmp; tmp=$(mktemp -d)
    local long; long=$(printf 'x%.0s' $(seq 1 400))
    run_from_fake_hook "g.sh" "$tmp" "\".claude/state/g.jsonl\" \"blocked\" \"$long\"" >/dev/null
    local row; row=$(cat "$tmp/.claude/state/g.jsonl" 2>/dev/null)
    local detail_len; detail_len=$(printf '%s' "$row" | python3 -c 'import json,sys; print(len(json.loads(sys.stdin.read()).get("detail","")))' 2>/dev/null)
    assert_eq "200" "$detail_len" "detail truncated to 200 chars"
    rm -rf "$tmp"
}

echo "=== test_hook_fire_log: the shared hook fire-logger ==="
run_test test_writes_a_row_a_consumer_can_read
run_test test_names_the_calling_hook_not_the_helper
run_test test_returns_zero_when_the_log_cannot_be_written
run_test test_empty_path_is_a_noop_not_an_error
run_test test_detail_is_truncated_because_it_is_a_label_not_a_transcript
report
