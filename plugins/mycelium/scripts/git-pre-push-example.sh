#!/usr/bin/env bash
# Mycelium canvas-validation pre-push hook (reference example).
#
# Installs to .git/hooks/pre-push to run validate_canvas.py before each push.
# Per-clone setup; .git/hooks/ is NOT version-controlled.
#
# To install in your repo:
#   cp "$CLAUDE_PLUGIN_ROOT/scripts/git-pre-push-example.sh" .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push
#
# Or call it from your existing hook tooling (husky, lefthook, the Python
# pre-commit framework, etc.) — see docs/contributing/README.md for the
# integration pattern.
#
# Emergency bypass: git push --no-verify
# (Document any use in your project's decision log; the hook exists for a reason.)

set -euo pipefail

# Resolve validate_canvas.py — prefer plugin cache (current install model);
# fall back to legacy in-tree locations for older installs.
VALIDATOR=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/validate_canvas.py" ]; then
    VALIDATOR="$CLAUDE_PLUGIN_ROOT/scripts/validate_canvas.py"
elif [ -f "plugins/mycelium/scripts/validate_canvas.py" ]; then
    VALIDATOR="plugins/mycelium/scripts/validate_canvas.py"
elif [ -f ".claude/scripts/validate_canvas.py" ]; then
    VALIDATOR=".claude/scripts/validate_canvas.py"
fi

if [ -z "$VALIDATOR" ]; then
    echo "[mycelium pre-push] validate_canvas.py not found — skipping canvas validation." >&2
    echo "  Set CLAUDE_PLUGIN_ROOT or install the Mycelium plugin to enable this check." >&2
    exit 0
fi

if [ ! -d ".claude/canvas" ]; then
    # No canvas in this project; nothing to validate.
    exit 0
fi

echo "[mycelium pre-push] Validating canvas via ${VALIDATOR##*mycelium/} ..." >&2
if ! python3 "$VALIDATOR" >&2; then
    echo "" >&2
    echo "[mycelium pre-push] Canvas validation FAILED — push blocked." >&2
    echo "  • Fix the errors above and re-push." >&2
    echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
    exit 1
fi

# Layer 2 (graduated v0.23.22 after named-attribution-leak recurrence #3):
# If this repo carries the framework's template validator (tests/validate-
# template.sh), run it too. This surfaces Check 33 (named-attribution leak
# scan) and the other structural-integrity checks at push-time. Downstream
# user projects do not ship tests/ — they'll skip this branch gracefully.
TEMPLATE_VALIDATOR=""
if [ -f "tests/validate-template.sh" ]; then
    TEMPLATE_VALIDATOR="tests/validate-template.sh"
elif [ -f ".claude/tests/validate-template.sh" ]; then
    TEMPLATE_VALIDATOR=".claude/tests/validate-template.sh"
fi

if [ -n "$TEMPLATE_VALIDATOR" ]; then
    echo "[mycelium pre-push] Validating template integrity via $TEMPLATE_VALIDATOR ..." >&2
    if ! bash "$TEMPLATE_VALIDATOR" >&2; then
        echo "" >&2
        echo "[mycelium pre-push] Template validation FAILED — push blocked." >&2
        echo "  • Fix the errors above and re-push." >&2
        echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
        exit 1
    fi
fi

# Layer 3 (added v0.49.14 after the delivery-discipline-never-fired reckoning,
# 2026-06-18): run the CI-equivalent delivery-quality gate LOCALLY at push-time.
# This is the first mechanism that makes Mycelium's own test/clean-code discipline
# fire automatically on framework-dev — previously it lived only in validate.yml
# (CI), so untested scripts (check_legacy_paths shipped at 0%) and CI-only-red
# commits (v0.49.7/9) sailed past every local check. Hard-blocks. Framework repo
# only (tests/python present); downstream user projects skip this branch.
SCRIPTS_DIR=""
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/scripts" ]; then
    SCRIPTS_DIR="$CLAUDE_PLUGIN_ROOT/scripts"
elif [ -d "plugins/mycelium/scripts" ]; then
    SCRIPTS_DIR="plugins/mycelium/scripts"
fi

# RESOLVE A PYTHON THAT CAN ACTUALLY IMPORT THE TEST DEPS (v0.110.5).
#
# This gate used to invoke `python3 -m pytest` and report "Tests FAILED" on any
# non-zero exit — including the exit that means "pytest is not installed for this
# interpreter". Measured 2026-08-16 on a dev machine: a version manager took over
# `python3` the previous day, the new interpreter had no pytest, and the gate
# reported failing tests while 906 tests passed under a working runner. A gate
# whose MESSAGE does not match its CONDITION sends the reader to debug the wrong
# thing — the same defect this release fixes in shell-safety-guard's backtick rule.
#
# Order: uv with the declared CI requirements (no global install, pinned
# versions), else a python3 that can import pytest, else FAIL LOUDLY AND
# DISTINCTLY as "cannot run", never as "failed".
PYRUN=""
if command -v uv >/dev/null 2>&1 && [ -f requirements-ci.txt ]; then
    PYRUN="uv run --with-requirements requirements-ci.txt python"
elif python3 -c "import pytest" >/dev/null 2>&1; then
    PYRUN="python3"
fi

if [ -d "tests/python" ] && [ -n "$SCRIPTS_DIR" ] && [ -z "$PYRUN" ]; then
    echo "" >&2
    echo "[mycelium pre-push] TEST GATE CANNOT RUN — this is NOT a test failure." >&2
    echo "  python3 resolves to: $(command -v python3)" >&2
    echo "  and it cannot import pytest; uv is unavailable or requirements-ci.txt is missing." >&2
    echo "  • Install uv (recommended — no global installs, honours the pinned versions), or" >&2
    echo "  • make pytest importable by that interpreter." >&2
    echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
    exit 1
fi

if [ -d "tests/python" ] && [ -n "$SCRIPTS_DIR" ]; then
    # TESTS RUN LOCALLY; COVERAGE MEASUREMENT DOES NOT. Changed 2026-08-31 (v0.150.0).
    #
    # WHAT IT COST TO LEARN THIS. With `--cov` this step took 192s and the whole hook
    # ~366s. Two failures on one day, both caused by the duration and neither looking
    # like it: (1) git opens its connection to the remote BEFORE running this hook, so
    # GitHub closed the idle SSH connection mid-run and every push died with SIGPIPE
    # after all gates had PASSED — an error naming nothing about SSH; (2) the agent
    # reached for `--no-verify` because the hook was slow, skipped the fail-open gate it
    # did not know was in here, and put a red commit on main.
    #
    # The literature says the same thing and names the failure mode exactly: fast lint at
    # pre-commit, the test suite at pre-push, slow/comprehensive in CI — because a local
    # suite that "takes long enough that developers disable the hook entirely" is worse
    # than one that never ran. That is not a hypothetical here; it happened.
    #
    # WHAT IS NOT LOST. CI runs the SAME suite with `--cov-fail-under=85` AND
    # `check_coverage_floor.py --floor 70` (validate.yml). Coverage is still ENFORCED,
    # just not twice. Hooks are early feedback; enforcement lives in CI and branch
    # protection. Coverage instrumentation is what costs the time — the identical suite
    # runs in ~78s without it, so the safety net stays and the tax goes.
    echo "[mycelium pre-push] Delivery-quality gate: tests, no coverage (runner: $PYRUN) ..." >&2
    if ! $PYRUN -m pytest tests/python/ -q >&2; then
        echo "" >&2
        echo "[mycelium pre-push] Tests FAILED — push blocked." >&2
        echo "  • Coverage is NOT measured here; CI enforces both the 85% total and the" >&2
        echo "    70% per-file floor. A push that passes here can still go red on coverage." >&2
        exit 1
    fi
    # THE GATE SET IS DECLARED, NOT HARD-CODED HERE (v0.110.0).
    #
    # This block used to run four scripts by name. CI ran eleven. Measured
    # 2026-08-09 the two lists had drifted by SEVEN gates — seven classes of
    # defect that could only ever surface as a red build after a push. That is
    # the 2026-06-18 "local validation != CI gates" correction recurring, and it
    # recurred because the fix was a list in a second file rather than one list.
    #
    # `local-gate-set.txt` is now the single source, and `check_gate_parity.py`
    # (itself in the set) fails the push if CI gains a gate the set has not got.
    GATE_SET="$SCRIPTS_DIR/local-gate-set.txt"
    if [ ! -f "$GATE_SET" ]; then
        # Do NOT skip silently. In a framework tree (tests/python present) an
        # absent gate set means the gates are not running, and a hook that
        # reports nothing while checking nothing is anti-pattern #9 in the one
        # place it would be least visible.
        echo "[mycelium pre-push] Gate set not found at $GATE_SET — the delivery-quality gates did NOT run." >&2
        echo "  This is a framework tree, so that is a defect, not a clean skip. Push blocked." >&2
        echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
        exit 1
    fi

    echo "[mycelium pre-push] Delivery-quality gate: declared gate set ..." >&2
    while IFS= read -r gate_line || [ -n "$gate_line" ]; do
        case "$gate_line" in
            ''|'#'*|'!waived '*) continue ;;
        esac
        # shellcheck disable=SC2086  # args are intentionally word-split
        set -- $gate_line
        gate_script="$1"; shift
        if [ ! -f "$SCRIPTS_DIR/$gate_script" ]; then
            echo "[mycelium pre-push] Gate set names $gate_script, which is not in $SCRIPTS_DIR — push blocked." >&2
            exit 1
        fi
        if ! python3 "$SCRIPTS_DIR/$gate_script" "$@" >&2; then
            echo "" >&2
            echo "[mycelium pre-push] $gate_script FAILED — push blocked." >&2
            echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
            exit 1
        fi
    done < "$GATE_SET"

    rm -f coverage.json
fi

# SELF-DRIFT WARNING (v0.110.0). `.git/hooks/` is not version-controlled, so an
# installed copy of this hook goes stale silently: the shipped example gains a
# gate, every clone keeps running the old one, and nothing says so. Measured
# 2026-08-09 on the framework author's own machine — the installed hook was one
# gate behind the shipped example and had been for weeks.
#
# WARNS, DOES NOT BLOCK. An operator may legitimately customise their hook, and
# blocking a push over a diff from an example would be coercion rather than
# scaffolding (theory-tensions #7). It also cannot be a hard check: this hook has
# no way to know whether a difference is drift or intent.
if [ -n "${SCRIPTS_DIR:-}" ] && [ -f "$SCRIPTS_DIR/git-pre-push-example.sh" ] && [ -f "$0" ]; then
    if ! cmp -s "$0" "$SCRIPTS_DIR/git-pre-push-example.sh"; then
        echo "[mycelium pre-push] NOTE: this installed hook differs from the shipped example." >&2
        echo "  If that is not deliberate, refresh it:" >&2
        echo "    cp \"$SCRIPTS_DIR/git-pre-push-example.sh\" .git/hooks/pre-push && chmod +x .git/hooks/pre-push" >&2
    fi
fi

exit 0
