#!/usr/bin/env bash
# tests/bash/test_brownfield-gate.sh
# Coverage proof for hooks/brownfield-gate.sh.
#
# The gap this guards, measured by roadmap auto-dogfood 2026-07-28: on a project
# that already has code, discovery-gate.sh fires on Write only and exempts
# Edit/MultiEdit by design, so an edit-shaped request sailed straight through
# (blocking:0, no PreToolUse at all) and the agent shipped a code change with no
# canvas and no discovery. A SessionStart prose nudge was tried first, was
# delivered (723 bytes, 8.2% of context), and was ignored.
#
# Scenario-per-guardpost: bad path blocks on BOTH Write and Edit; happy paths
# (greenfield, discovery already engaged, wrong tool) stay silent; the one-shot
# guarantee holds via either ack file.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$REPO_ROOT/plugins/mycelium/hooks/brownfield-gate.sh"

GATE_ERR_FILE="$(mktemp)"
trap 'rm -f "$GATE_ERR_FILE"' EXIT
run_gate() {
    local pdir="$1" json="$2"
    printf '%s' "$json" | CLAUDE_PROJECT_DIR="$pdir" bash "$GATE" 2>"$GATE_ERR_FILE"
    echo $?
}
gate_err() { cat "$GATE_ERR_FILE"; }

tool_json() { printf '{"tool_name":"%s","tool_input":{"file_path":"src/thing.py"}}' "$1"; }

# A project with real pre-existing source and no discovery state.
make_brownfield_project() {
    local tmp; tmp=$(mktemp -d)
    mkdir -p "$tmp/.claude/diamonds" "$tmp/.claude/canvas" "$tmp/.claude/state" "$tmp/src"
    # 12+ source files is the threshold for "real project, not a stray script".
    for i in $(seq 1 15); do echo "def f${i}(): pass" > "$tmp/src/mod${i}.py"; done
    echo "active_diamonds: []" > "$tmp/.claude/diamonds/active.yml"
    printf '# purpose\n' > "$tmp/.claude/canvas/purpose.yml"   # stub, under 60 bytes
    echo "$tmp"
}

# ---------------------------------------------------------------- BAD PATHS
# The whole point: Edit must block. This is the case that was completely
# ungated before, and it is where most brownfield work lives.
P=$(make_brownfield_project)
assert_eq "2" "$(run_gate "$P" "$(tool_json Edit)")" \
    "brownfield + Edit blocks (the previously-ungated case)"
assert_contains "$(gate_err)" "/mycelium:adopt" \
    "block message names the adopt on-ramp"
assert_contains "$(gate_err)" "brownfield-ack" \
    "block message names the escape hatch"
assert_contains "$(gate_err)" "ONCE" \
    "block message states the one-shot guarantee"

assert_eq "2" "$(run_gate "$P" "$(tool_json Write)")" \
    "brownfield + Write blocks too"
assert_eq "2" "$(run_gate "$P" "$(tool_json MultiEdit)")" \
    "brownfield + MultiEdit blocks too"
rm -rf "$P"

# --------------------------------------------------------------- HAPPY PATHS
# Greenfield must NOT trip this — that is /mycelium:start's job.
P=$(mktemp -d); mkdir -p "$P/.claude/state"
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "greenfield (no source) stays silent"
rm -rf "$P"

# Below the 12-file threshold: a stray script is not a brownfield project.
P=$(mktemp -d); mkdir -p "$P/.claude/state" "$P/src"
for i in 1 2 3; do echo "x = $i" > "$P/src/s${i}.py"; done
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "under the source-count threshold stays silent"
rm -rf "$P"

# Discovery already engaged, via a populated diamond.
P=$(make_brownfield_project)
printf 'active_diamonds:\n  - id: l0-purpose\n    phase: discover\n' > "$P/.claude/diamonds/active.yml"
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "populated diamond means not a brownfield entry"
rm -rf "$P"

# Discovery already engaged, via a populated purpose.yml (>60 bytes).
P=$(make_brownfield_project)
printf 'why: |\n  We help maintainers see what their codebase cannot tell them about itself.\n' \
    > "$P/.claude/canvas/purpose.yml"
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "populated purpose.yml means not a brownfield entry"
rm -rf "$P"

# Tools the gate has no business touching.
P=$(make_brownfield_project)
assert_eq "0" "$(run_gate "$P" "$(tool_json Read)")" \
    "Read is not gated"
assert_eq "0" "$(run_gate "$P" "$(tool_json Bash)")" \
    "Bash is not gated"
rm -rf "$P"

# -------------------------------------------------------- ONE-SHOT GUARANTEE
# The load-bearing promise: it interrupts once and never again, whichever way
# the user answered. Without this it becomes nagging, and nagging gets the
# plugin uninstalled — enforcement used for acquisition.
P=$(make_brownfield_project)
assert_eq "2" "$(run_gate "$P" "$(tool_json Edit)")" "fires before ack"
echo "2026-07-28: user said carry on" > "$P/.claude/state/brownfield-ack"
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "silent after brownfield-ack (one-shot holds)"
assert_eq "0" "$(run_gate "$P" "$(tool_json Write)")" \
    "one-shot holds across tools"
rm -rf "$P"

# A user who already declined discovery wholesale has answered this too.
P=$(make_brownfield_project)
echo "2026-07-28: user declined discovery" > "$P/.claude/state/discovery-skip-ack"
assert_eq "0" "$(run_gate "$P" "$(tool_json Edit)")" \
    "existing discovery-skip-ack satisfies this gate"
rm -rf "$P"

# ------------------------------------------------------------------ FAIL-OPEN
# A hook must never take a session down. Malformed stdin passes through.
P=$(make_brownfield_project)
assert_eq "0" "$(run_gate "$P" 'not json at all')" \
    "malformed input fails open"
assert_eq "0" "$(run_gate "$P" '{}')" \
    "empty payload fails open"
rm -rf "$P"

report
