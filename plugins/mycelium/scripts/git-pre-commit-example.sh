#!/usr/bin/env bash
# Mycelium derived-token pre-commit hook (reference example).
#
# WHY THIS EXISTS, AND IT IS NOT "ONE MORE GATE"
# ----------------------------------------------
# Every mechanical-consistency gate in this repo runs PRE-PUSH. That is one gate
# too late, and 2026-09-20 showed exactly how it fails:
#
#   1. A release commit set plugin.json to 0.228.0 and left CLAUDE.md's canonical
#      `*Version` line at 0.227.3. Check 40 (`sync_derived.py --check`) detects
#      this state precisely -- run against that commit it exits 1 and names the
#      file -- but Check 40 runs on push, and no push happened.
#   2. Later work repaired the working tree.
#   3. The push then passed 27/27, because the gates only ever see the TIP.
#
# The broken commit is now permanent. Nothing downstream can repair it, and
# Check 26 reads history, so it fired on that commit in every session afterwards.
# A pre-push gate cannot protect history; it can only protect the tip. The state
# a commit is made in is only checkable at commit time, so the check belongs here.
#
# THE INVARIANT
# -------------
# Derived tokens match their canonical source. Canonical is CLAUDE.md's
# `*Version X.Y.Z` line and the count of `plugins/mycelium/skills/*/SKILL.md`;
# everything else (plugin.json, marketplace.json, the system card, the skill
# indexes) is generated FROM those. Committing a derived file that disagrees with
# canonical is how a release ships claiming a version it is not.
#
# Remediation is one command and it is printed on failure:
#     python3 plugins/mycelium/scripts/sync_derived.py
#
# WHAT THIS HOOK CANNOT DO -- stated because a check whose limits are undocumented
# gets read as coverage it does not have:
#   - IT VALIDATES THE WORKING TREE, NOT THE INDEX. `sync_derived.py` reads files
#     from disk, so a partial `git add` can still commit a drifted subset while the
#     working tree is clean. Check 40 pre-push remains the backstop for that case.
#     This hook closes the common failure (drift present on disk at commit time),
#     not every reachable one.
#   - It says nothing about whether the version bump is the RIGHT one. Semver
#     judgement is Check 26's job and a human's; see engine/version-discipline.md.
#   - `--no-verify` bypasses it, as with every git hook.
#
# INSTALL (per clone; .git/hooks/ is not version-controlled):
#     cp plugins/mycelium/scripts/git-pre-commit-example.sh .git/hooks/pre-commit
#     chmod +x .git/hooks/pre-commit
#
# Emergency bypass: git commit --no-verify
# (Document any use in the decision log; the hook exists for a reason.)

set -euo pipefail

SYNC_SCRIPT=""
if [ -f "plugins/mycelium/scripts/sync_derived.py" ]; then
    SYNC_SCRIPT="plugins/mycelium/scripts/sync_derived.py"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/sync_derived.py" ]; then
    SYNC_SCRIPT="$CLAUDE_PLUGIN_ROOT/scripts/sync_derived.py"
fi

# sync_derived.py derives from the FRAMEWORK repo's own layout. A consumer project
# has no plugins/mycelium/ tree of its own, so there is nothing here to check and
# the hook gets out of the way rather than failing on an absence.
if [ -z "$SYNC_SCRIPT" ] || [ ! -d "plugins/mycelium/skills" ] || [ ! -f "CLAUDE.md" ]; then
    exit 0
fi

# PICK AN INTERPRETER, AND SAY SO WHEN NONE WORKS. A bare `python3` that is absent
# or broken exits non-zero, which this hook would otherwise report as "drift" --
# a tool failure dressed up as a finding. Same defect the pre-push hook documents.
PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[mycelium pre-commit] no python interpreter found — derived-token check SKIPPED (not passed)." >&2
    exit 0
fi

output=$("$PY" "$SYNC_SCRIPT" --check 2>&1) || {
    # A NON-ZERO EXIT IS NOT AUTOMATICALLY A FINDING. sync_derived.py exits 1 for
    # drift, but it also exits 1 on an unhandled exception — a missing target file
    # raises FileNotFoundError and prints a traceback. Reporting that as "drift"
    # would be a tool failure dressed up as a finding, which is the same defect the
    # pre-push hook documents for a broken interpreter. Blocking is still correct
    # (fail closed), but the reason has to be the true one.
    if printf '%s' "$output" | grep -q '^Traceback'; then
        echo "[mycelium pre-commit] sync_derived.py FAILED TO RUN — commit blocked, and this is NOT a drift finding." >&2
        echo >&2
        printf '%s\n' "$output" | sed 's/^/  /' >&2
        echo >&2
        echo "  The derived-token invariant was NOT checked. Fix the script or the missing" >&2
        echo "  file above, then commit; do not read this as 'no drift'." >&2
        exit 1
    fi
    echo "[mycelium pre-commit] DERIVED TOKENS DRIFT FROM CANONICAL — commit blocked." >&2
    echo >&2
    printf '%s\n' "$output" | sed 's/^/  /' >&2
    echo >&2
    echo "  Canonical: CLAUDE.md '*Version X.Y.Z' and the count of plugins/mycelium/skills/*/SKILL.md." >&2
    echo "  Everything above is GENERATED from those — edit canonical, then regenerate:" >&2
    echo >&2
    echo "      $PY $SYNC_SCRIPT" >&2
    echo >&2
    echo "  Committing this state is how a release ships claiming a version it is not." >&2
    echo "  A pre-push gate cannot repair it afterwards, because the commit is permanent." >&2
    exit 1
}

exit 0
