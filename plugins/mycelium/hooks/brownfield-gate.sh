#!/bin/bash
# Mycelium brownfield gate (PreToolUse; Write AND Edit/MultiEdit)
#
# Asks ONCE, ever, per project: this repo has code and no discovery state —
# do you want Mycelium to read it, or shall we carry on?
#
# WHY THIS EXISTS, measured rather than assumed (2026-07-28):
#   - discovery-gate.sh fires on Write only and exempts Edit/MultiEdit by
#     design. On a project that already has code, most work is EDIT-shaped, so
#     that gate covers the minority of brownfield work. Two auto-dogfood runs:
#     a file-creating request on a TS extension gated cleanly (blocking:1,
#     agent stopped); an edit-shaped request on a Python library sailed through
#     (blocking:0, no PreToolUse at all) and the agent shipped a code change
#     with no canvas and no discovery.
#   - A SessionStart prose nudge was tried FIRST and measurably did not work.
#     v0.65.0's CHECK 11 was delivered (723 bytes, 8.2% of context) and the
#     agent ignored it, shipping the change anyway with an identical score.
#     That is this project's own thesis landing on its own fix: prose gates get
#     read as recommendations; a hook is what makes a gate real.
#
# WHY ONE-SHOT. Blocking a maintainer from editing their own working project
# would be enforcement used for acquisition — the mistake the adoption research
# warns about, and the fastest way to get the plugin uninstalled. So this fires
# on the FIRST substantive tool use and never again, whichever way the user
# answers. It buys exactly one interruption to ask one question.
#
# Contract:
#   - PreToolUse on Write|Edit|MultiEdit
#   - Fires only when: existing source present AND no discovery state AND no ack
#   - exit 2 (block + message) once; exit 0 forever after
#   - Escape hatch: .claude/state/brownfield-ack — records the USER's answer

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
# shellcheck disable=SC2034  # INPUT is read by hi_read_input in the sourced library
INPUT=$(cat)
[ -f "$PROJECT_DIR/.claude/state/brownfield-ack" ] && exit 0
[ -f "$PROJECT_DIR/.claude/state/discovery-skip-ack" ] && exit 0
HI_LIB="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input_read.sh"
# shellcheck source=/dev/null
. "$HI_LIB"
hi_read_input
if [ -n "$HI_BAD" ]; then
  hi_deny "Mycelium brownfield gate: refused, tool input is not the documented shape ($HI_BAD)."
fi
case "$HI_TOOL" in
  Write|Edit|MultiEdit|NotebookEdit|Bash|mcp__filesystem__write_file|mcp__filesystem__edit_file) ;;
  *) exit 0 ;;
esac
# Only a write to SOURCE fires this gate. Writes under .claude/ (the ack file, the canvas) do not:
# 2026-09-11 the documented remedy, writing the ack, was itself blocked by this gate.
TOUCHES_SOURCE=0
while IFS=$'\t' read -r target _exists _size; do
  case "$target" in
    ""|GUARD:*|OUTSIDE:*) ;;
    OPAQUE:*) TOUCHES_SOURCE=1;;
    .claude/*|*/.claude/*) ;;
    *) TOUCHES_SOURCE=1;;
  esac
done <<< "$HI_TARGETS"
[ "$TOUCHES_SOURCE" = "1" ] || exit 0

hi_discovery_engaged && exit 0

SRC_COUNT=$(find "$PROJECT_DIR" \
    \( -path "$PROJECT_DIR/.git" -o -path "$PROJECT_DIR/.claude" \
       -o -path "$PROJECT_DIR/plugins" -o -name node_modules -o -name vendor \
       -o -name .venv -o -name dist -o -name build \) -prune -o \
    -type f \( -iname '*.py' -o -iname '*.ts' -o -iname '*.tsx' -o -iname '*.js' \
       -o -iname '*.jsx' -o -iname '*.mjs' -o -iname '*.go' -o -iname '*.rs' -o -iname '*.rb' \
       -o -iname '*.java' -o -iname '*.kt' -o -iname '*.swift' -o -iname '*.cs' \
       -o -iname '*.php' -o -iname '*.vue' -o -iname '*.svelte' -o -iname '*.c' \
       -o -iname '*.cc' -o -iname '*.cpp' -o -iname '*.h' -o -iname '*.hpp' -o -iname '*.sh' \
       -o -iname '*.scala' -o -iname '*.sql' -o -iname '*.dart' -o -iname '*.lua' \
       -o -iname '*.ex' -o -iname '*.exs' -o -iname '*.zig' -o -iname '*.hs' \) -print 2>/dev/null \
  | head -30 | wc -l | tr -d ' ')

# 12+ source files means a real project, not a stray script or fresh scaffold.
[ "${SRC_COUNT:-0}" -ge 12 ] || exit 0

cat >&2 <<EOF
Mycelium brownfield gate: this project has source code (${SRC_COUNT}+ files) and
no discovery state — no diamond, no populated purpose.yml. The code came first,
so do NOT open /mycelium:start as if this were a blank page: it asks a
maintainer of a shipping product to articulate purpose from scratch.

Ask the user, once, and then act on their answer:

1. /mycelium:adopt — reads this repo and populates what the code CAN establish
   (delivery and solution shape), then works the remaining holes with them the
   way a greenfield project would. The canvas is simply not empty when it
   starts. Roughly 10-30 minutes to a real starting position.

2. Carry on with what they asked for. Perfectly legitimate — they may just want
   the change made.

EITHER WAY, record the answer so this never interrupts again: write
.claude/state/brownfield-ack containing the date and the user's own words, then
retry. This gate fires ONCE per project, whichever way they answer.

Do not write the ack file on your own judgment — it records the USER's decision,
not yours. And do not treat this as permission to skip the work they asked for;
if they say carry on, carry on.
EOF
. "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
mycelium_log_fire ".claude/state/brownfield-gate-fires.jsonl" "blocked" 2>/dev/null || true
exit 2
