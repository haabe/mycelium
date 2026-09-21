#!/bin/bash
# Mycelium discovery gate (PreToolUse, Write only)
#
# Blocks scaffolding NEW source files in a project where discovery has never
# been engaged — no active diamond, no populated purpose.yml — and the user
# has not explicitly acknowledged skipping discovery.
#
# Provenance: the deliver-framed-opening routing gap. A confident "build me
# X" first message on an empty workspace led the agent to scaffold code with
# zero discovery behind it — observed in founder dogfood (2026-06-08/09) and
# mechanically reproduced by the roadmap auto-dogfood battery (2026-07-02:
# both runs of the bad-path scenario wrote source files to the turn cap).
# Router-discipline prose alone did not hold; this gate is the teeth.
#
# Scope is deliberately NARROW (the friction-wall risk is real):
#   - Fires ONLY on the Write tool (Edit/MultiEdit never blocked — brownfield
#     work on existing code is untouched).
#   - Fires ONLY when the target file does not exist yet (new-file scaffolds).
#   - Fires ONLY for source/infra-shaped files (extension + basename lists).
#   - Fires ONLY when discovery has never been engaged: no diamond entry in
#     active.yml AND no populated canvas/purpose.yml.
#   - Escape hatch: .claude/state/discovery-skip-ack — written AFTER the user
#     explicitly declines discovery (record the date + the user's own words).
#     One conversation per project, then the gate is silent forever.
#
# Exit 0 = allow, Exit 2 = block (stderr is shown to the agent).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

# shellcheck disable=SC2034  # INPUT is read by hi_read_input in the sourced library
INPUT=$(cat)
HI_LIB="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input_read.sh"
# shellcheck source=/dev/null
. "$HI_LIB"
hi_read_input
if [ -n "$HI_BAD" ]; then
  hi_deny "Mycelium discovery gate: refused, tool input is not the documented shape ($HI_BAD)."
fi
case "$HI_TOOL" in
  Write|NotebookEdit|Bash|mcp__filesystem__write_file) ;;
  *) exit 0 ;;   # Edit/MultiEdit need an existing file; the brownfield gate covers those
esac

# A NEW gated source file: absent, or present and empty (2026-09-11: `touch` then Write passed
# the old existence test). Real path inside the project, not under .claude, not prose.
GATED_FILE=""
while IFS=$'\t' read -r target exists size; do
  case "$target" in ""|OUTSIDE:*|GUARD:*|OPAQUE:*|.claude/*|*/.claude/*) continue;; esac
  if [ "$exists" = "1" ] && [ "${size:-0}" -gt 0 ]; then continue; fi
  base="${target##*/}"
  case "$base" in
    Dockerfile*|docker-compose*|Makefile|CMakeLists.txt|requirements.txt|pyproject.toml|package.json|Cargo.toml|go.mod|Gemfile|Rakefile|build.gradle|pom.xml|Pipfile|tsconfig.json) GATED_FILE="$target"; break;;
    *.md|*.txt|*.rst) continue;;
  esac
  lower="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.py|*.pyw|*.js|*.mjs|*.cjs|*.ts|*.mts|*.cts|*.tsx|*.jsx|*.vue|*.svelte|*.html|*.htm|*.css|*.scss|*.go|*.rs|*.java|*.kt|*.kts|*.scala|*.rb|*.php|*.c|*.cc|*.cpp|*.h|*.hpp|*.cs|*.swift|*.m|*.mm|*.sql|*.sh|*.bash|*.zsh|*.ps1|*.lua|*.dart|*.ex|*.exs|*.erl|*.hs|*.clj|*.zig|*.nim|*.jl|*.r|*.pl|*.tf|*.ipynb) GATED_FILE="$target"; break;;
  esac
done <<< "$HI_TARGETS"
[ -n "$GATED_FILE" ] || exit 0
BASENAME="${GATED_FILE##*/}"

[ -f "$PROJECT_DIR/.claude/state/discovery-skip-ack" ] && exit 0
hi_discovery_engaged && exit 0

cat >&2 <<EOF
Mycelium discovery gate: this project has no discovery state yet (no active
diamond, no populated purpose.yml), and you are about to scaffold a new
source file ($BASENAME). Building on an unexamined idea is the framework's
most consistently observed failure mode — do NOT silently proceed.

Instead:
1. Offer the user the ~10-minute discovery brief first: /mycelium:start
   (it captures what they want to change, for whom, and the riskiest
   assumption — THEN building starts on the same footing).
2. If the user EXPLICITLY declines and wants to build without discovery,
   record that choice: write .claude/state/discovery-skip-ack containing
   the date and the user's own words, then retry. The gate stays silent
   for this project afterwards.

Do not write the ack file on your own judgment — it records the USER's
decision, not yours.
EOF
. "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked" 2>/dev/null || true
exit 2
