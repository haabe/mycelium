#!/usr/bin/env bash
# tests/bash/test_gates_wrapper.sh
#
# Coverage proof for scripts/gates.sh.
#
# THE DEFECT IT EXISTS FOR (2026-08-07): `bash tests/validate-template.sh | tail -4 &&
# git commit` reads TAIL's exit status, not the gate's. `tail` succeeds at printing a
# failure, so the && chain saw success and a commit landed on a red gate. The same
# exit-status trap fired three times in one session.
#
# "Never pipe a gate" is a rule, and rules rot — the reply-owed rule had two
# implementations and only one got fixed. So the fix is a script, and this is the
# proof that the script REFUSES rather than merely reports.
#
# Scenario-per-guardpost:
#   happy — all gates pass                 -> exit 0, "ALL PASSED"
#   sad   — one gate fails                 -> NON-ZERO, names the gate
#   bad   — a gate is missing              -> NON-ZERO (absent is not passing), exit 3
#   bad   — a failing gate shows evidence  -> the tail of its output reaches stderr
#   bad   — verdict survives a pipe        -> the verdict line is on stderr too
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "    ✓ : $1"; }
bad() { FAIL=$((FAIL+1)); echo "    ✗ : $1"; }

# A sandbox repo with fake gates, so the test never runs the real 800-test suite.
mk_repo() {
  local d; d="$(mktemp -d)"
  mkdir -p "$d/scripts" "$d/tests/python" "$d/tests/bash"
  cp "$REPO/scripts/gates.sh" "$d/scripts/gates.sh"
  printf '#!/usr/bin/env bash\nexit %s\n' "${1:-0}" > "$d/tests/validate-template.sh"
  printf '#!/usr/bin/env bash\nexit 0\n' > "$d/tests/bash/run.sh"
  # A REAL passing test, not an empty file. pytest exits 5 on "no tests collected",
  # and the wrapper is right to refuse that — nothing was verified. The fixture has to
  # represent a genuinely passing repo, or it tests the wrapper's honesty by accident.
  printf 'def test_stub():\n    assert True\n' > "$d/tests/python/test_stub.py"
  printf '[lint]\n' > "$d/ruff.toml"
  echo "$d"
}

echo "  gates wrapper"

# --- sad: a failing gate must make the wrapper fail -------------------------
# THE CORE ASSERTION. If this ever exits 0, the wrapper has become decoration and
# the defect it was built for is back.
D="$(mk_repo 1)"
OUT="$(cd "$D" && bash scripts/gates.sh 2>&1)"; RC=$?
if [ "$RC" -ne 0 ]; then ok "a failing gate produces a NON-ZERO exit (got $RC)"
else bad "failing gate exited 0 — the wrapper does not refuse"; fi
case "$OUT" in
  *"validate-template"*) ok "the failing gate is named in the output" ;;
  *) bad "output does not name the failing gate" ;;
esac
case "$OUT" in
  *"DO NOT COMMIT"*) ok "a failure says what not to do next" ;;
  *) bad "failure verdict carries no instruction" ;;
esac
rm -rf "$D"

# --- happy: all gates pass -------------------------------------------------
D="$(mk_repo 0)"
OUT="$(cd "$D" && bash scripts/gates.sh 2>&1)"; RC=$?
if [ "$RC" -eq 0 ]; then ok "all gates passing exits 0"
else bad "all-passing run exited $RC"; fi
case "$OUT" in
  *"ALL PASSED"*) ok "a pass says so explicitly" ;;
  *) bad "passing run does not state it passed" ;;
esac
rm -rf "$D"

# --- bad: an absent gate is not a passing gate -----------------------------
D="$(mk_repo 0)"; rm -f "$D/tests/validate-template.sh"
OUT="$(cd "$D" && bash scripts/gates.sh 2>&1)"; RC=$?
if [ "$RC" -ne 0 ]; then ok "a MISSING gate fails rather than passes (got $RC)"
else bad "missing gate exited 0 — nothing was verified and it read green"; fi
case "$OUT" in
  *"INCOMPLETE"*|*"not found"*) ok "the missing gate is named" ;;
  *) bad "missing-gate run does not say what was absent" ;;
esac
rm -rf "$D"

# --- bad: the verdict must reach stderr, so a stdout pipe cannot hide it ----
D="$(mk_repo 1)"
ERRONLY="$(cd "$D" && bash scripts/gates.sh 2>&1 >/dev/null)"
case "$ERRONLY" in
  *"FAILED"*) ok "the failure verdict is on stderr, not only stdout" ;;
  *) bad "piping stdout away hides the verdict — the original defect" ;;
esac
rm -rf "$D"

echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
