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
# IT VALIDATES THE INDEX, NOT THE WORKING TREE, AND THAT IS THE WHOLE DESIGN
# --------------------------------------------------------------------------
# A commit records the INDEX. A hook that reads the disk is answering a question
# nobody asked, and the gap between the two is precisely where a partial
# `git add` lives. v0.230.0 shipped this hook reading the working tree, with the
# limitation written in this header -- which closed the common case and left the
# named one open. Documenting a hole is not closing it. Both directions were
# wrong:
#
#   * Stage a drifted plugin.json, then put the working tree back: the commit
#     carries the drift and a disk-reading hook sees a spotless tree and passes.
#     That is the original defect, reachable in one more step.
#   * Edit a file without staging it: the commit is clean and a disk-reading hook
#     blocks anyway. A gate that cries wolf on work in progress is a gate people
#     disable by habit -- which switches it off for the case it was built for.
#
# HOW, and the choice of mechanism matters:
#   `git checkout-index --all --prefix=$TMP/` materialises exactly what the commit
#   will contain into a scratch directory, then the checker runs against that with
#   `--root`. It is READ-ONLY with respect to your work: it never touches the
#   worktree, the index, or any ref.
#
#   The widely-copied alternative, `git stash --keep-index`, is rejected here on
#   purpose. It MUTATES the working tree to perform a read, so an interrupted hook
#   -- Ctrl-C, a crash, a failing checker that exits before the pop -- can leave
#   uncommitted work in a stash the author does not know exists. A verification
#   step must not be able to lose the thing it is verifying.
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
#     python3 plugins/mycelium/scripts/sync_derived.py && git add -u
#
# WHAT THIS HOOK STILL CANNOT DO -- stated because a check whose limits are
# undocumented gets read as coverage it does not have:
#   - It says nothing about whether the version bump is the RIGHT one. Semver
#     judgement is Check 26's job and a human's; see engine/version-discipline.md.
#   - DURING A MERGE OR REBASE WITH CONFLICTS it steps aside, because an unmerged
#     index cannot be materialised and a half-resolved tree is not a commit state
#     worth judging. Check 40 pre-push remains the backstop for that window.
#   - `--no-verify` bypasses it, as with every git hook.
#
# INSTALL (per clone; .git/hooks/ is not version-controlled):
#     cp plugins/mycelium/scripts/git-pre-commit-example.sh .git/hooks/pre-commit
#     chmod +x .git/hooks/pre-commit
#
# Emergency bypass: git commit --no-verify
# (Document any use in the decision log; the hook exists for a reason.)

set -euo pipefail

# Not a git repo at all (or git is unavailable): nothing to validate.
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$ROOT" ] || exit 0
cd "$ROOT" || exit 0

# AN UNMERGED INDEX CANNOT BE MATERIALISED. `git checkout-index` fails on
# conflicted paths, and a half-resolved tree is not a state worth ruling on. Step
# aside loudly rather than reporting a tooling limit as a finding.
if [ -n "$(git ls-files --unmerged 2>/dev/null)" ]; then
    echo "[mycelium pre-commit] unresolved merge conflicts — derived-token check SKIPPED (not passed)." >&2
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

STAGED_TREE=$(mktemp -d)
cleanup() { rm -rf "$STAGED_TREE"; }
trap cleanup EXIT

# Materialise the index — exactly what this commit will contain.
if ! git checkout-index --all --prefix="$STAGED_TREE/" 2>/dev/null; then
    echo "[mycelium pre-commit] could not materialise the index — derived-token check SKIPPED (not passed)." >&2
    exit 0
fi

# Resolve the checker FROM THE STAGED TREE where possible, so the committed state
# is validated by the committed logic — the same principle as reading the index
# rather than the disk. Falls back to the working copy for consumers installing
# the hook without the framework tree.
SYNC_SCRIPT=""
if [ -f "$STAGED_TREE/plugins/mycelium/scripts/sync_derived.py" ]; then
    SYNC_SCRIPT="$STAGED_TREE/plugins/mycelium/scripts/sync_derived.py"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$CLAUDE_PLUGIN_ROOT/scripts/sync_derived.py" ]; then
    SYNC_SCRIPT="$CLAUDE_PLUGIN_ROOT/scripts/sync_derived.py"
fi

# sync_derived.py derives from the FRAMEWORK repo's own layout. A consumer project
# has no plugins/mycelium/ tree of its own, so there is nothing here to check and
# the hook gets out of the way rather than failing on an absence. Judged on the
# STAGED tree, because that is what is being committed.
if [ -z "$SYNC_SCRIPT" ] \
   || [ ! -d "$STAGED_TREE/plugins/mycelium/skills" ] \
   || [ ! -f "$STAGED_TREE/CLAUDE.md" ]; then
    exit 0
fi

output=$("$PY" "$SYNC_SCRIPT" --check --root "$STAGED_TREE" 2>&1) || {
    # A NON-ZERO EXIT IS NOT AUTOMATICALLY A FINDING. sync_derived.py exits 1 for
    # drift, but it also exits 1 on an unhandled exception — a missing target file
    # raises FileNotFoundError and prints a traceback. Reporting that as "drift"
    # would be a tool failure dressed up as a finding, which is the same defect the
    # pre-push hook documents for a broken interpreter. Blocking is still correct
    # (fail closed), but the reason has to be the true one.
    if printf '%s' "$output" | grep -q '^Traceback'; then
        echo "[mycelium pre-commit] sync_derived.py FAILED TO RUN — commit blocked, and this is NOT a drift finding." >&2
        echo >&2
        printf '%s\n' "$output" | sed "s|$STAGED_TREE|<staged>|g; s/^/  /" >&2
        echo >&2
        echo "  The derived-token invariant was NOT checked. Fix the script or the missing" >&2
        echo "  file above, then commit; do not read this as 'no drift'." >&2
        exit 1
    fi
    echo "[mycelium pre-commit] DERIVED TOKENS DRIFT FROM CANONICAL — commit blocked." >&2
    echo >&2
    # Paths below are inside the scratch copy of your index; rewrite them so they
    # read as the repo paths the author has to go and fix.
    printf '%s\n' "$output" | sed "s|$STAGED_TREE/||g; s|$STAGED_TREE|.|g; s/^/  /" >&2
    echo >&2
    echo "  THIS IS ABOUT WHAT YOU ARE COMMITTING, NOT WHAT IS ON DISK. The check ran" >&2
    echo "  against your staged index, so a file you fixed but did not 'git add' is" >&2
    echo "  still drifted in this commit." >&2
    echo >&2
    echo "  Canonical: CLAUDE.md '*Version X.Y.Z' and the count of plugins/mycelium/skills/*/SKILL.md." >&2
    echo "  Everything above is GENERATED from those — edit canonical, then regenerate AND stage:" >&2
    echo >&2
    echo "      $PY plugins/mycelium/scripts/sync_derived.py && git add -u" >&2
    echo >&2
    echo "  Committing this state is how a release ships claiming a version it is not." >&2
    echo "  A pre-push gate cannot repair it afterwards, because the commit is permanent." >&2
    exit 1
}

exit 0
