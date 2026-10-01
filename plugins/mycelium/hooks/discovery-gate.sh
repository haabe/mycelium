#!/bin/bash
# Mycelium discovery gate (PreToolUse; Write, and since v0.291.0 Edit/MultiEdit once discovery is engaged)
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
#   - New files on Write; since v0.291.0 also edits to product code (Edit, MultiEdit,
#     the MCP edit tool) ONCE DISCOVERY IS ENGAGED, outside declared `prototype_paths`.
#     Where discovery has not started, edits stay untouched (the brownfield gate's case).
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
# EDITS COUNT AS BUILDING ONCE DISCOVERY IS ENGAGED (v0.291.0, phase migration stage 0b-2). Until
# then Edit and MultiEdit exited here, so a prototype could be edited into the product with no gate
# firing (dogfood decision log 2026-09-30, the run-10 replay). In a project where discovery has not
# started, edits stay untouched: the brownfield gate asks there, once.
EDITING=0
case "$HI_TOOL" in
  Write|NotebookEdit|Bash|mcp__filesystem__write_file) ;;
  Edit|MultiEdit|mcp__filesystem__edit_file) EDITING=1 ;;
  *) exit 0 ;;
esac

# A NEW gated source file: absent, or present and empty (2026-09-11: `touch` then Write passed
# the old existence test). Real path inside the project, not under .claude, not prose.
GATED_FILE=""
GATED_ALL=()  # every gated target the write makes (v0.307.6, control audit P11): an ack's scope
              # and the declared-prototype exemption were judged on the first one only
while IFS=$'\t' read -r target exists size; do
  case "$target" in ""|OUTSIDE:*|GUARD:*|OPAQUE:*|.claude/*|*/.claude/*) continue;; esac
  if [ "$EDITING" = "0" ] && [ "$exists" = "1" ] && [ "${size:-0}" -gt 0 ]; then continue; fi
  base="${target##*/}"
  case "$base" in
    Dockerfile*|docker-compose*|Makefile|CMakeLists.txt|requirements.txt|pyproject.toml|package.json|Cargo.toml|go.mod|Gemfile|Rakefile|build.gradle|pom.xml|Pipfile|tsconfig.json) GATED_ALL+=("$target"); continue;;
    *.md|*.txt|*.rst) continue;;
  esac
  lower="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    *.py|*.pyw|*.js|*.mjs|*.cjs|*.ts|*.mts|*.cts|*.tsx|*.jsx|*.vue|*.svelte|*.html|*.htm|*.css|*.scss|*.go|*.rs|*.java|*.kt|*.kts|*.scala|*.rb|*.php|*.c|*.cc|*.cpp|*.h|*.hpp|*.cs|*.swift|*.m|*.mm|*.sql|*.sh|*.bash|*.zsh|*.ps1|*.lua|*.dart|*.ex|*.exs|*.erl|*.hs|*.clj|*.zig|*.nim|*.jl|*.r|*.pl|*.tf|*.ipynb) GATED_ALL+=("$target");;
  esac
done <<< "$HI_TARGETS"
[ "${#GATED_ALL[@]}" -gt 0 ] && GATED_FILE="${GATED_ALL[0]}"
if [ -z "$GATED_FILE" ]; then
  # THE PRODUCT IS NOT ALWAYS CODE (v0.270.0): a new file in the project's declared
  # `product_paths` (a service's documents, a course's lessons) is building, whatever its kind.
  CANDIDATES=()
  while IFS=$'\t' read -r target exists size; do
    case "$target" in ""|OUTSIDE:*|GUARD:*|OPAQUE:*|.claude/*|*/.claude/*) continue;; esac
    if [ "$EDITING" = "0" ] && [ "$exists" = "1" ] && [ "${size:-0}" -gt 0 ]; then continue; fi
    CANDIDATES+=("$target")
  done <<< "$HI_TARGETS"
  if [ "${#CANDIDATES[@]}" -gt 0 ]; then
    PF_HELPER="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input.py"
    [ -f "$PF_HELPER" ] || PF_HELPER="${CLAUDE_PLUGIN_ROOT:-}/scripts/_hook_input.py"
    for c in "${CANDIDATES[@]}"; do
      hit="$(python3 "$PF_HELPER" --project-dir "$PROJECT_DIR" --product-file "$c" 2>/dev/null)" \
        && GATED_ALL+=("$hit")
    done
    [ "${#GATED_ALL[@]}" -gt 0 ] && GATED_FILE="${GATED_ALL[0]}"
  fi
fi
[ -n "$GATED_FILE" ] || exit 0
# Declared prototypes are free (v0.291.0): throwaway discovery code under `prototype_paths`.
# Releasing it is the decision to build, and the release gate holds that.
NP_HELPER="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input.py"
[ -f "$NP_HELPER" ] || NP_HELPER="${CLAUDE_PLUGIN_ROOT:-}/scripts/_hook_input.py"
if ! "$(mycelium_python)" "$NP_HELPER" --project-dir "$PROJECT_DIR" --not-prototype "${GATED_ALL[@]}" >/dev/null 2>&1; then
  exit 0
fi
BASENAME="${GATED_FILE##*/}"
ACT="create a new source file"
[ "$EDITING" = "1" ] && ACT="change product code"

hi_discovery_engaged; HI_ENGAGED=$?
# The user's discovery-skip-ack lifts the COLD-project gate only (v0.307.6, control audit P10).
# Until then it was read first and lifted the delivery stage too, for good, once the project
# started discovery; DL-1364 took that same "every future build, forever" out of the delivery ack.
if [ "$HI_ENGAGED" -eq 1 ] && [ -f "$PROJECT_DIR/.claude/state/discovery-skip-ack" ]; then
  exit 0
fi
if [ "$EDITING" = "1" ] && [ "$HI_ENGAGED" -eq 1 ]; then
  exit 0  # an edit in a project where discovery has not started: the brownfield gate's case
fi
if [ "$HI_ENGAGED" -eq 3 ]; then
  # Diamonds exist but cannot be read without PyYAML (v0.290.0): refuse with the real reason.
  mycelium_skip_ack build "${GATED_ALL[@]}" && exit 0  # dated, scoped, logged (v0.293.0)
  printf 'Mycelium delivery gate: you are about to %s (%s). %s\n' "$ACT" "$BASENAME" "$MYCELIUM_NO_YAML_FIX" >&2
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked-cannot-check" 2>/dev/null || true
  exit 2
fi
if [ "$HI_ENGAGED" -eq 0 ]; then
  # SECOND STAGE (v0.245.0): discovery is under way, so the question is whether this build sits
  # inside a delivery cycle whose whole chain holds (scripts/scale_locks.py): an open L3, L4 or
  # L5 with a purpose, a desired outcome and a target opportunity with evidence above it. Any
  # open L3 was not enough: /mycelium:start leaves a purpose and nothing else, so an L3 opened
  # straight after it builds on a guess, the "wrong thing right away" the scale locks exist to
  # stop. An end-to-end dogfood run shipped a release over 31 commits under an L0 in discover.
  mycelium_skip_ack build "${GATED_ALL[@]}" && exit 0  # dated, scoped, logged (v0.293.0)
  hi_delivery_state
  case $? in
    0) exit 0 ;;
    3)  # PyYAML missing: refuse and say how to fix it (v0.290.0; it allowed until then)
      printf 'Mycelium delivery gate: you are about to %s (%s). %s\n' "$ACT" "$BASENAME" "$MYCELIUM_NO_YAML_FIX" >&2
      . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
      mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked-cannot-check" 2>/dev/null || true
      exit 2 ;;
  esac
  # v0.307.6 (control audit P14): unquoted, so its backticks ran as commands and blanked the
  # remedy; they are escaped, the variables still expand.
  cat >&2 <<EOF
Mycelium delivery gate: you are about to $ACT ($BASENAME),
and no delivery cycle is ready to carry code. Code is written under an L3
(build to learn), L4 or L5 diamond whose parents have established what it
builds on, and which has committed to build (\`start_experiment\` and
\`commit_to_build\` recorded) with Four Risks and Privacy passed (a pilot is not
exempt). What is missing:

  ${HI_DELIVERY_WHY}

Each scale opens on its parent (engine/diamond-rules.md, Entry locks): L1 on
a purpose (who and why), L2 on a strategy (an L1 diamond, a North Star, the
landscape) and a desired outcome, L3 on a target opportunity with evidence in
an L2 diamond, L4 on an L3 at medium confidence, L5 on launch data. Produce
what is missing with the skill named above, open the L3 on its L2's target
(object_ref naming the opportunity, parent the L2), record its
\`start_experiment\` and \`commit_to_build\` with /mycelium:diamond-progress, then retry.
  python3 \${CLAUDE_PLUGIN_ROOT}/scripts/scale_locks.py --can-open L3
says what is still missing.

Only if the USER explicitly says this work should not be tracked, they record
.claude/state/delivery-skip-ack: \`recorded_at\`, \`expires\` (30 days by default),
\`covers\` (the paths it covers), \`releases: true\` only if releases are meant,
and their own words in \`why\`. Do not write the ack file on your own judgement.
EOF
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked-delivery" 2>/dev/null || true
  exit 2
fi

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
   the date and the user's own words, then retry. This gate stays silent
   for the project afterwards; once discovery starts (a diamond or a
   purpose), the delivery gate applies to code as in any other project.

Do not write the ack file on your own judgment — it records the USER's
decision, not yours.
EOF
. "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
mycelium_log_fire ".claude/state/discovery-gate-fires.jsonl" "blocked" 2>/dev/null || true
exit 2
