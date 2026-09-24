#!/bin/bash
# Mycelium preflight validation
# Creates a stamp file that the gate.sh checks before allowing code edits.
# This ensures corrections.md has been read and basic system health verified.

# Resolve the project dir. Prefer $CLAUDE_PROJECT_DIR (the Claude Code CLI sets
# it), but fall back to walking up from $PWD to find a .claude/ dir when it is
# unset. Some runtimes (e.g. Claude Cowork) do not provision CLAUDE_PROJECT_DIR,
# which made the bare ".-fallback resolve against the wrong directory and report
# "Memory not yet initialized" on every turn of an already-initialized project
# (Cowork dogfood F1, 2026-06-19). When the env var IS set we trust it verbatim,
# so CLI behaviour is unchanged.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_DIR" ]; then
  _d="$PWD"
  while [ -n "$_d" ] && [ "$_d" != "/" ]; do
    if [ -d "$_d/.claude" ]; then PROJECT_DIR="$_d"; break; fi
    _d="$(dirname "$_d")"
  done
  PROJECT_DIR="${PROJECT_DIR:-.}"
fi
CORRECTIONS_FILE="$PROJECT_DIR/.claude/memory/corrections.md"

# Stamp path: per-user + per-project under $TMPDIR — must match gate.sh exactly.
# See gate.sh for rationale (world-predictable shared /tmp path was the bug).
_stamp_uid=$(id -u 2>/dev/null || echo 0)
_stamp_phash=$(printf '%s' "$PROJECT_DIR" | { md5 2>/dev/null || md5sum 2>/dev/null; } | tr -cd '0-9a-f' | cut -c1-12)
STAMP_FILE="${TMPDIR:-/tmp}/mycelium-preflight-stamp-${_stamp_uid}-${_stamp_phash:-0}"

# Calculate corrections hash
CORRECTIONS_HASH="none"
if [ -f "$CORRECTIONS_FILE" ]; then
  if command -v md5 &>/dev/null; then
    CORRECTIONS_HASH=$(md5 -q "$CORRECTIONS_FILE")
  elif command -v md5sum &>/dev/null; then
    CORRECTIONS_HASH=$(md5sum "$CORRECTIONS_FILE" | cut -d' ' -f1)
  fi
fi

# Count corrections
#
# THIS NUMBER IS PRINTED INTO EVERY SESSION'S CONTEXT, before any work starts,
# which makes it the most-read quantity the framework produces and the one it
# was least careful about. Until 2026-08-09 the pattern here was `^### `, and it
# was wrong in both directions at once: it missed `##` and `####` entries, it
# missed the entire bullet form `- **Title (DATE, class)**:` that most recent
# entries use, and it counted section headings like `### Prevention rule` as
# corrections. Measured on the dogfood repo that day it said 100 against a real
# corpus of 141, and the gap had widened from 30 the day before — it degrades
# with use, because the invisible form is the one people write now.
#
# THE PATTERN BELOW MUST STAY EQUIVALENT TO `ENTRY_RE` in
# `scripts/_corrections_lib.py`. Bash cannot import it, so the equivalence is
# held by a test rather than by a shared symbol:
# `tests/python/test_correction_count_agreement.py` runs THIS hook against
# `tests/fixtures/corrections/mixed.md` and compares the banner it prints to the
# library's count. Change one without the other and that test fails.
CORRECTIONS_COUNT=0
if [ -f "$CORRECTIONS_FILE" ]; then
  # grep -c prints "0" AND exits 1 on no matches, so `|| echo 0` would append a
  # second "0" → "0\n0" → "integer expected" in the -eq test below. Use `|| true`
  # (grep already prints the count) and normalize to a bare integer.
  CORRECTIONS_COUNT=$(grep -cE '^#{2,4}[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}|^-[[:space:]]+\*\*[^*]*\([0-9]{4}-[0-9]{2}-[0-9]{2}[a-z]?[,)][^*]*\*\*' "$CORRECTIONS_FILE" 2>/dev/null || true)
  CORRECTIONS_COUNT=${CORRECTIONS_COUNT//[^0-9]/}
  CORRECTIONS_COUNT=${CORRECTIONS_COUNT:-0}
fi

# Write stamp (0600 — only the owner can read/clobber it)
rm -f "$STAMP_FILE"
( umask 077; cat > "$STAMP_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "corrections_hash": "$CORRECTIONS_HASH",
  "corrections_count": $CORRECTIONS_COUNT,
  "project_dir": "$PROJECT_DIR"
}
EOF
)

# Disambiguate "memory not yet initialized" from "memory has zero entries"
# from "memory has N entries" — bare "0 corrections" reads as a possible
# counting failure to first-run users (per opp-001).
# ------------------------------------------------------------
# BACKGROUND-CHECK DELIVERY (v0.186.0). The fast session-start tier announces the heavy
# checks as running in the background and leaves a pending marker; the async tier writes
# their text to session-checks.json. UserPromptSubmit stdout is added to context, so this
# is the documented place to deliver it. Delivered once per pending session; the advisory
# ledger settles here, on the full block, never on the partial one the fast tier emitted.
# ------------------------------------------------------------
_PF_CACHE="$PROJECT_DIR/.claude/state/session-checks.json"
_PF_PENDING="$PROJECT_DIR/.claude/state/session-checks.pending"
if [ -f "$_PF_PENDING" ] && [ -f "$_PF_CACHE" ]; then
  _PF_SID="$(cat "$_PF_PENDING" 2>/dev/null || echo "")"
  _PF_BLOCK="$(python3 -c '
import json, sys
sid, path = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except Exception as e:  # SPEAKS: an unreadable cache is an undelivered heavy tier, and says so below
    print("__UNREADABLE__ " + type(e).__name__ + ": " + str(e)[:120], end="")
    sys.exit(0)
if d.get("session") == sid and d.get("delivered_to") != sid and d.get("reminders"):
    print(d["reminders"], end="")
' "$_PF_SID" "$_PF_CACHE" 2>/dev/null || true)"
  case "$_PF_BLOCK" in
    __UNREADABLE__*)
      echo "MYCELIUM: the background session-start checks could not be delivered (${_PF_BLOCK#__UNREADABLE__ }); run /mycelium:canvas-health for them."
      rm -f "$_PF_PENDING"
      _PF_BLOCK=""
      ;;
  esac
  if [ -n "$_PF_BLOCK" ]; then
    _PF_LEDGER="${CLAUDE_PLUGIN_ROOT:-}/scripts/advisory_ledger.py"
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$_PF_LEDGER" ] && [ "${MYCELIUM_ADVISORY_LEDGER:-on}" != "off" ]; then
      # Keyed on the start that produced the block (session id + the cache's own epoch), so a
      # resumed session with the same id still settles; see session-start.sh for the reason.
      _PF_EPOCH="$(python3 -c 'import json,sys; print(int(float(json.load(open(sys.argv[1])).get("generated_epoch") or 0)))' "$_PF_CACHE" 2>/dev/null || date +%s)"
      _PF_SETTLED="$(printf '%s' "$_PF_BLOCK" | python3 "$_PF_LEDGER" settle --project-dir "$PROJECT_DIR" --session "${_PF_SID}@${_PF_EPOCH}" 2>&1)"
      [ -n "$_PF_SETTLED" ] && _PF_BLOCK="$_PF_SETTLED"
    fi
    echo "MYCELIUM FEEDBACK LOOPS (background run, delivered now): ${_PF_BLOCK}"
    python3 -c '
import json, sys
sid, path = sys.argv[1], sys.argv[2]
d = json.load(open(path)); d["delivered_to"] = sid; json.dump(d, open(path, "w"))
' "$_PF_SID" "$_PF_CACHE" 2>/dev/null || true
    rm -f "$_PF_PENDING"
  fi
fi

# ------------------------------------------------------------
# DISCOVERY PRE-WARNING (v0.222.0). Same condition as hooks/discovery-gate.sh, read
# through the same function, so the two cannot drift: no skip-ack, no discovery state.
# WHY HERE: the gate binds, but late. Measured 2026-09-17 on a build-framed opening in
# an empty project, 0 of 3 runs routed to discovery; the model drafted the whole data
# model, and only then met the gate refusing the write. The routing rule arrives at
# SessionStart as prose and did not hold. This line gives the model the gate's verdict
# BEFORE it does the work the gate exists to prevent. State-keyed, not prompt-keyed: it
# reads no words from the prompt, and it goes silent for good once discovery state or
# the user's skip-ack exists. It asks for nothing on a prompt that is not a build.
# ------------------------------------------------------------
# COST: this runs on every prompt of every project, and the strict check is a python
# start (~0.2 s, measured 2026-09-17). So a grep goes first: a purpose.yml with a worded
# `why:` or an active.yml with an `id:` entry LOOKS engaged, and the python is skipped.
# The grep can be fooled by a hand-faked file where the strict parse cannot; being
# fooled means silence, which is the safe direction for an advisory, and the gate
# still runs the strict parse before it allows a write.
_PF_HI_LIB="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input_read.sh"
_PF_LOOKS_ENGAGED=0
if grep -qE '^[[:space:]]*why:[[:space:]]*["'"'"'>|]?[[:space:]]*[[:alnum:]]' "$PROJECT_DIR/.claude/canvas/purpose.yml" 2>/dev/null \
   || grep -qE '^[[:space:]]*-[[:space:]]+id:[[:space:]]*[[:alnum:]]' "$PROJECT_DIR/.claude/diamonds/active.yml" 2>/dev/null; then
  _PF_LOOKS_ENGAGED=1
fi
if [ "$_PF_LOOKS_ENGAGED" -eq 0 ] && [ -f "$_PF_HI_LIB" ] && [ ! -f "$PROJECT_DIR/.claude/state/discovery-skip-ack" ]; then
  # shellcheck source=/dev/null
  . "$_PF_HI_LIB"
  if ! hi_discovery_engaged; then
    echo "MYCELIUM DISCOVERY STATE: none in this project (no purpose, no active diamond). If this prompt asks you to design or build something, new source files WILL BE REFUSED by the discovery gate, so do not draft the design first: ask who it is for, what problem it solves and what evidence there is, or offer /mycelium:start. If the prompt is not a build request, ignore this line and answer it."
  fi
elif [ "$_PF_LOOKS_ENGAGED" -eq 1 ] && [ ! -f "$PROJECT_DIR/.claude/state/delivery-skip-ack" ] \
     && ! grep -qE '^[[:space:]]*scale:[[:space:]]*["'"'"']?L[345]\b' "$PROJECT_DIR/.claude/diamonds/active.yml" 2>/dev/null; then
  # The discovery gate's second stage (v0.245.0) refuses new source files until an L3/L4/L5 whose
  # chain holds is open (scripts/scale_locks.py). Said once per prompt, cheaply, so the agent builds
  # the chain before drafting code rather than after a refusal. A grep, like the check above: fooled
  # means silence, and the gate parses strictly.
  echo "MYCELIUM DELIVERY STATE: no diamond that delivers (L3, L4 or L5) is open. If this prompt asks you to build or change code, the chain comes first, because each scale opens on its parent: a desired outcome (/mycelium:ost-builder), a target opportunity with evidence, then an L3 whose object_ref names it. The discovery gate refuses new source files until then; scripts/scale_locks.py --can-open L3 says what is missing. If the prompt is not a build request, ignore this line and answer it."
fi
# The scale locks read YAML. Without PyYAML they cannot be checked, and both gates then allow every
# write; this line is what makes that fail-open speak (fail-open-reviewed.yml, scale_locks.py).
if [ "$_PF_LOOKS_ENGAGED" -eq 1 ] && ! python3 -c 'import yaml' 2>/dev/null; then
  echo "MYCELIUM: the scale locks are NOT being checked on this machine (PyYAML is not installed: pip install pyyaml). Until it is, nothing stops a diamond opening before its parent is ready or code being written outside a delivery cycle."
fi

if [ ! -f "$CORRECTIONS_FILE" ]; then
  echo "Mycelium preflight complete. Memory not yet initialized — run /mycelium:setup if this is a fresh install."
elif [ "$CORRECTIONS_COUNT" -eq 0 ]; then
  echo "Mycelium preflight complete. Memory is empty (no corrections logged yet)."
else
  echo "Mycelium preflight complete. $CORRECTIONS_COUNT corrections in memory."
fi
exit 0
