#!/usr/bin/env bash
# gates.sh — run every pre-ship gate and report a status you cannot accidentally lose.
#
# WHY THIS EXISTS, AND IT IS NOT THAT ANYONE FORGOT A RULE.
#
# The gates were already good. The way they get RUN was the defect:
#
#     bash tests/validate-template.sh | tail -4 && git commit ...
#
# A pipeline's exit status is the status of its LAST command. `tail` succeeds at
# printing a failure, so the `&&` reads success and the commit lands on red. That
# happened on 2026-08-07: validate-template FAILED, the commit went through, and it
# was only caught because someone re-read the output by eye. The same trap fired
# three times in that one session.
#
# "Never pipe a gate" is a rule, and rules rot — the reply-owed rule had two
# implementations and only one got fixed. So this is not a rule. It is a script that
# captures each gate's own exit status BEFORE anything can mask it, and refuses to
# report a pass it did not earn.
#
# USE:
#   bash scripts/gates.sh          # run all, human-readable
#   bash scripts/gates.sh --quiet  # only the verdict line
#
# EXIT 0 only when every gate passed. Anything else is non-zero, including a gate
# that could not be found — an absent gate is not a passing gate.
#
# PIPING THIS IS SAFE. The verdict goes to stderr as well as stdout, and the exit
# status is this script's own, so `bash scripts/gates.sh | tail -1 && ...` still
# reports THIS script's failure through the pipeline's last command... which is
# `tail`. It cannot fix that for you, so it prints a loud verdict line instead of a
# quiet one, and the ONE rule that remains is in the banner below.
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

FAILED=()
PASSED=()
MISSING=()

run_gate() {
  local name="$1"; shift
  local logfile
  logfile="$(mktemp)"
  # No pipe. The status captured here is the gate's own.
  "$@" >"$logfile" 2>&1
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    PASSED+=("$name")
    [ "$QUIET" -eq 1 ] || echo "  PASS  $name"
  else
    FAILED+=("$name (exit $rc)")
    echo "  FAIL  $name (exit $rc)" >&2
    # Show the tail of a failing gate: a verdict with no evidence sends the reader hunting.
    tail -12 "$logfile" | sed 's/^/        /' >&2
  fi
  rm -f "$logfile"
}

[ "$QUIET" -eq 1 ] || echo "Running pre-ship gates..."

if [ -f tests/validate-template.sh ]; then
  run_gate "validate-template" bash tests/validate-template.sh
else
  MISSING+=("tests/validate-template.sh")
fi

if [ -d tests/python ]; then
  run_gate "pytest" python3 -m pytest tests/python -q
else
  MISSING+=("tests/python")
fi

if [ -f tests/bash/run.sh ]; then
  run_gate "bash-suite" bash tests/bash/run.sh
else
  MISSING+=("tests/bash/run.sh")
fi

if command -v ruff >/dev/null 2>&1 && [ -f ruff.toml ]; then
  run_gate "ruff" ruff check --config ruff.toml
else
  MISSING+=("ruff or ruff.toml")
fi

echo ""
if [ "${#MISSING[@]}" -gt 0 ]; then
  # An absent gate is not a passing gate. Say which, and fail.
  echo "GATES: INCOMPLETE — ${#MISSING[@]} gate(s) not found: ${MISSING[*]}" | tee /dev/stderr
  echo "Nothing was verified for those. This is not a clean result." | tee /dev/stderr
  exit 3
fi

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo "GATES: FAILED — ${#FAILED[@]} of $(( ${#PASSED[@]} + ${#FAILED[@]} )): ${FAILED[*]}" | tee /dev/stderr
  echo "DO NOT COMMIT. If you reached this through a pipe, the pipe's exit status is NOT this one." | tee /dev/stderr
  exit 1
fi

echo "GATES: ALL PASSED (${#PASSED[@]}/${#PASSED[@]}) — ${PASSED[*]}" | tee /dev/stderr
exit 0
