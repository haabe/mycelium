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

# G-V14: the architecture fitness functions belong in the command run after a change,
# "not only in CI". They were ALREADY blocking at pre-push — the 2026-08-23 rule census
# missed that because the pre-push hook is DATA-DRIVEN off local-gate-set.txt and names
# none of them, so a grep for the script name finds only validate.yml and reads as
# "CI-only". They were never CI-only. What WAS true: this command, the one a builder
# actually runs after a change, ran four gates against fifteen in the gate set.
#
# Driven off the same single source as CI and pre-push, so the three surfaces cannot
# drift apart again — check_gate_parity.py already asserts CI is a subset of the gate
# set, and this closes the last surface that read a different list.
GATE_SET="plugins/mycelium/scripts/local-gate-set.txt"
if [ -f "$GATE_SET" ]; then
  while IFS= read -r gate_line || [ -n "$gate_line" ]; do
    case "$gate_line" in ''|'#'*) continue ;; esac
    # `!waived <script> <reason>` is DIRECTIVE syntax in the gate set, not a gate name.
    # git-pre-push-example.sh has skipped it since it was introduced and
    # check_gate_parity.py parses it; this reader never learned it, so every local run
    # reported `FAIL !waived — named in gate set, not on disk` and the verdict line was
    # red on a clean tree. A gate runner that is always red trains you to ignore it,
    # which is the failure this whole script exists to prevent. Three readers of one
    # file, one of them never updated — the reply-owed shape again.
    # Reported rather than silently skipped: an invisible waiver is how a gate set
    # quietly shrinks (anti-pattern #9), which the not-on-disk branch below guards.
    case "$gate_line" in
      '!waived '*)
        waived_rest="${gate_line#!waived }"
        echo "  WAIVE $waived_rest"
        continue
        ;;
    esac
    # shellcheck disable=SC2086 -- gate_line carries its own arguments by design
    set -- $gate_line
    gate_script="$1"; shift
    if [ ! -f "plugins/mycelium/scripts/$gate_script" ]; then
      # A gate NAMED in the set but absent on disk is a failure, never a skip: a gate
      # set that quietly shrinks reports green while checking less (anti-pattern #9).
      FAILED+=("$gate_script (named in gate set, not on disk)")
      echo "  FAIL  $gate_script — named in $GATE_SET but not in plugins/mycelium/scripts" >&2
      continue
    fi
    if [ "$gate_script" = "check_coverage_floor.py" ]; then
      # DEFERRED, AND SAID OUT LOUD RATHER THAN DROPPED. Its input is a fresh
      # coverage.json, produced by the pytest-with-coverage step that CI and the
      # pre-push hook run and this command deliberately does not (plain pytest here is
      # seconds, coverage is minutes). Running it here would either read a STALE
      # coverage.json from some earlier run — green on numbers nobody just measured —
      # or fail on a precondition the builder did not break. Both are worse than
      # naming it. It still blocks at pre-push and in CI.
      [ "$QUIET" -eq 1 ] || echo "  DEFER check_coverage_floor — needs a fresh coverage.json; runs at pre-push and in CI"
      continue
    fi
    run_gate "${gate_script%.py}" python3 "plugins/mycelium/scripts/$gate_script" "$@"
  done < "$GATE_SET"
fi
# NO `else` BRANCH, DELIBERATELY. An absent gate set means this is not the framework
# repo — a consumer project running the shipped wrapper has no plugins/mycelium/scripts.
# Treating that as a missing gate would fail every consumer for a defect they cannot
# have. The framework repo is covered because check_gate_parity.py (itself in the set)
# fails loudly if the set and CI disagree.

# RESOLVE RUNNERS THAT CAN ACTUALLY RUN (2026-08-16).
# `python3 -m pytest` and a bare `ruff` both assume the tool is reachable from
# whatever interpreter is first on PATH. When a version manager changes that
# interpreter, the gate stops being able to run and says so as MISSING — which is
# honest, but leaves a repo unable to pass its own gate on a machine where the
# tools exist under a different interpreter. uv resolves both with no global
# install, honouring requirements-ci.txt when the project declares one.
PYTEST_RUN=""
RUFF_RUN=""
if command -v uv >/dev/null 2>&1; then
  if [ -f requirements-ci.txt ]; then
    PYTEST_RUN="uv run --quiet --with-requirements requirements-ci.txt python -m pytest"
    RUFF_RUN="uv run --quiet --with-requirements requirements-ci.txt ruff"
  else
    PYTEST_RUN="uv run --quiet --with pytest python -m pytest"
    RUFF_RUN="uv run --quiet --with ruff ruff"
  fi
fi
if [ -z "$PYTEST_RUN" ] && python3 -c "import pytest" >/dev/null 2>&1; then
  PYTEST_RUN="python3 -m pytest"
fi
if [ -z "$RUFF_RUN" ] && command -v ruff >/dev/null 2>&1; then
  RUFF_RUN="ruff"
fi

if [ -d tests/python ] && [ -n "$PYTEST_RUN" ]; then
  run_gate "pytest" $PYTEST_RUN tests/python -q
elif [ -d tests/python ]; then
  MISSING+=("a runner for pytest (install uv, or make pytest importable)")
else
  MISSING+=("tests/python")
fi

if [ -f tests/bash/run.sh ]; then
  run_gate "bash-suite" bash tests/bash/run.sh
else
  MISSING+=("tests/bash/run.sh")
fi

if [ -n "$RUFF_RUN" ] && [ -f ruff.toml ]; then
  run_gate "ruff" $RUFF_RUN check --config ruff.toml
elif [ -f ruff.toml ]; then
  MISSING+=("a runner for ruff (install uv, or put ruff on PATH)")
else
  MISSING+=("ruff.toml")
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
