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

if [ -d "tests/python" ] && [ -n "$SCRIPTS_DIR" ]; then
    echo "[mycelium pre-push] Delivery-quality gate: tests + total-coverage floor ..." >&2
    if ! python3 -m pytest tests/python/ \
            --cov=plugins/mycelium/scripts --cov=plugins/mycelium/integrations \
            --cov-report=json --cov-fail-under=85 -q >&2; then
        echo "" >&2
        echo "[mycelium pre-push] Tests / total-coverage gate FAILED — push blocked." >&2
        echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
        exit 1
    fi
    echo "[mycelium pre-push] Delivery-quality gate: per-file coverage floor (every shipped script must be tested) ..." >&2
    if ! python3 "$SCRIPTS_DIR/check_coverage_floor.py" --root . --floor 70 >&2; then
        echo "" >&2
        echo "[mycelium pre-push] Per-file coverage floor FAILED — a shipped script lacks a test. Push blocked." >&2
        echo "  • Add tests/python/test_<name>.py exercising the flagged script(s)." >&2
        echo "  • Emergency bypass: git push --no-verify (and document it)." >&2
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
