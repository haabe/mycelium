#!/usr/bin/env bash
#
# Mycelium → opencode skill provisioner (project-local vendoring).
#
# WHY: opencode discovers skills natively (reads .claude/skills/) but does NO
# ${...} interpolation of skill content, and its read tool treats a literal
# ${CLAUDE_PLUGIN_ROOT}/... path as project-relative → fails. 38 of 58 skills
# reference ${CLAUDE_PLUGIN_ROOT}/engine/… + /harness/… in load-bearing steps.
# (Verified against opencode 1.17.7, 2026-06-15: setting the env var does NOT fix
# this — resolution would depend on the model cat-ing via a shell, i.e. model-luck.)
#
# WHAT: copy the Mycelium skills + their referenced engine/harness/jit-tooling/
# domains files INTO the project's .claude/, and rewrite ${CLAUDE_PLUGIN_ROOT}/
# references to project-relative paths the opencode read tool resolves deterministically.
#
# SCOPE: opencode-only / opt-in. Invoked by /mycelium:setup Step 5 when opencode is
# the runtime. Claude Code users never run this (they read skills from the plugin cache).
#
# STALENESS: the vendored copies are a SNAPSHOT, not a live link — they go stale when
# the framework updates. Re-run this (or /mycelium:setup) after a framework upgrade to
# refresh. The script is idempotent: it copies fresh each run, then rewrites, so re-runs
# are safe and produce the same result.
#
# DUAL-AGENT CAVEAT: on a project used with BOTH Claude Code and opencode, the vendored
# .claude/skills/ copies may duplicate the plugin-cache skills Claude Code already loads.
# Provision only on opencode-primary projects.
#
# Usage: provision-skills.sh [PROJECT_ROOT]   (defaults to $PWD)

set -euo pipefail

# Resolve the plugin root in priority order so this works whether invoked by
# /mycelium:setup (CLAUDE_PLUGIN_ROOT set) OR run by hand from a git clone
# (CLAUDE_PLUGIN_ROOT unset — the common opencode case). The script lives at
# <plugin_root>/integrations/opencode/provision-skills.sh, so its own location
# resolves the plugin root for a clone without the user setting anything.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/skills" ]; then
  PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}"                       # Claude Code / explicit
elif [ -d "$SCRIPT_DIR/../../skills" ]; then
  PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"            # running from a git clone
else
  PLUGIN_ROOT="$HOME/.claude/plugins/cache/mycelium-plugin/mycelium"  # cache fallback
fi
PROJECT_ROOT="${1:-$PWD}"
DEST="$PROJECT_ROOT/.claude"
VENDOR="$DEST/mycelium"

if [ ! -d "$PLUGIN_ROOT/skills" ]; then
  echo "ERROR: cannot find the Mycelium plugin (no skills/ dir at '$PLUGIN_ROOT')." >&2
  echo "       Run this script from inside a Mycelium checkout, or set" >&2
  echo "       CLAUDE_PLUGIN_ROOT to the plugins/mycelium path and re-run." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# GUARD 1 (fail-closed): the project root must be a git root.
#
# WHY THIS IS FAIL-CLOSED AND NOT A WARNING. opencode resolves its "project
# directory" by walking UP from the working directory until it finds a marker.
# From a directory with no .git, it escapes upward and adopts an ancestor repo
# as the project — so canvas writes, vendored skills, and CLAUDE.md edits land
# in the WRONG repository. A user with a dotfiles repo in $HOME (common) who
# does `mkdir ~/myidea && cd ~/myidea && opencode` gets writes into ~/. That is
# data loss, not friction, so this refuses rather than warns.
#
# `git init` is the fix and it is cheap, so the failure mode of this guard
# (someone has to type one command) is far cheaper than the failure it prevents.
# Recorded as opp-009 in the dogfood project; the anchor fix previously existed
# only in a dogfood-local runner and never shipped to consumers.
#
# ESCAPE HATCH: MYCELIUM_ALLOW_NONGIT_ROOT=1 for the deliberate case (a project
# tracked by another VCS, or a sandbox the user genuinely wants). It is opt-in
# and named, so bypassing is a decision rather than an accident.
# ---------------------------------------------------------------------------
if [ ! -d "$PROJECT_ROOT/.git" ] && [ "${MYCELIUM_ALLOW_NONGIT_ROOT:-0}" != "1" ]; then
  echo "ERROR: '$PROJECT_ROOT' is not a git root (no .git directory)." >&2
  echo "" >&2
  echo "  opencode finds its project directory by walking UP from the working" >&2
  echo "  directory. Without a marker here, it adopts an ancestor repository" >&2
  echo "  instead, and Mycelium's writes land in the wrong repo." >&2
  echo "" >&2
  echo "  Fix (one command):   git init" >&2
  echo "" >&2
  echo "  Deliberate exception: MYCELIUM_ALLOW_NONGIT_ROOT=1 $0 $PROJECT_ROOT" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# GUARD 2 (fail-closed): refuse to vendor into the Mycelium checkout itself.
#
# The documented manual setup path said `git clone … && cd mycelium` and then
# `provision-skills.sh .` with the comment "'.' = your project root" — but after
# the cd, '.' IS the clone. Following the docs literally vendored Mycelium into
# Mycelium: 58 skills copied over themselves and their ${CLAUDE_PLUGIN_ROOT}
# references rewritten in place, corrupting the checkout. The doc is fixed, and
# this catches anyone following an older copy of it.
# ---------------------------------------------------------------------------
if [ "$(cd "$PROJECT_ROOT" && pwd -P)" = "$(cd "$PLUGIN_ROOT/../.." && pwd -P 2>/dev/null || echo /nonexistent)" ] \
   || [ -f "$PROJECT_ROOT/plugins/mycelium/manifest.yml" ]; then
  echo "ERROR: '$PROJECT_ROOT' looks like the Mycelium checkout itself, not your project." >&2
  echo "" >&2
  echo "  Provisioning here would vendor Mycelium into Mycelium and rewrite the" >&2
  echo "  checkout's own skill references in place." >&2
  echo "" >&2
  echo "  Pass YOUR project root explicitly:" >&2
  echo "    bash $0 /path/to/your-project" >&2
  exit 1
fi

echo "Mycelium → opencode provisioning"
echo "  plugin:  $PLUGIN_ROOT"
echo "  project: $PROJECT_ROOT"

# 1. Skills → .claude/skills/ (opencode discovers these natively). Copy fresh.
mkdir -p "$DEST/skills"
cp -R "$PLUGIN_ROOT/skills/." "$DEST/skills/"

# 2. Referenced framework dirs → .claude/mycelium/<dir>/. Copy fresh.
mkdir -p "$VENDOR"
for d in engine harness jit-tooling domains; do
  if [ -d "$PLUGIN_ROOT/$d" ]; then
    rm -rf "${VENDOR:?}/$d"
    mkdir -p "$VENDOR/$d"
    cp -R "$PLUGIN_ROOT/$d/." "$VENDOR/$d/"
  fi
done

# 3. Rewrite ${CLAUDE_PLUGIN_ROOT}/ references to project-relative paths.
#    Order matters: the more-specific skills/ rewrite first, then the general one.
#    Handles both ${CLAUDE_PLUGIN_ROOT} and $CLAUDE_PLUGIN_ROOT forms.
#    Portable in-place sed (BSD + GNU): -i.bak then remove the backup.
rewrite() {
  local target="$1"
  find "$target" -type f \( -name '*.md' -o -name '*.yml' -o -name '*.yaml' \) -print0 \
    | while IFS= read -r -d '' f; do
        sed -i.bak -E \
          -e 's#\$\{?CLAUDE_PLUGIN_ROOT\}?/skills/#.claude/skills/#g' \
          -e 's#\$\{?CLAUDE_PLUGIN_ROOT\}?/#.claude/mycelium/#g' \
          "$f"
        rm -f "$f.bak"
      done
}
rewrite "$DEST/skills"
rewrite "$VENDOR"

# 4. Report. Only flag PATH-shaped residuals (a `/` after the var) — those are genuine
#    unrewritten references. Bare prose mentions of the variable name (e.g. setup/SKILL.md's
#    "do NOT expand $CLAUDE_PLUGIN_ROOT", or version-discipline.md's leaky-abstraction
#    discussion) are intentional and must NOT trip the warning (don't cry wolf).
RESIDUAL_RE='\$\{?CLAUDE_PLUGIN_ROOT\}?/'
SKILL_N=$(find "$DEST/skills" -name 'SKILL.md' | wc -l | tr -d ' ')
# NOTE the `|| true`. grep exits 1 when it finds NOTHING, which here is the
# SUCCESS case (every reference rewritten). Under `set -euo pipefail` that exit
# propagated through the pipeline into the assignment and killed the script — so
# a perfectly clean provisioning run aborted at exit 1 with no message, while a
# run that left residuals behind completed and printed "Done." The success path
# was the failure path, and /mycelium:setup Step 5 invokes this, so setup
# reported failure on a flawless run. Shipped broken; found 2026-07-25 by the
# first test that ever ran this script against a clean project root.
RESIDUAL=$( { grep -rlE "$RESIDUAL_RE" "$DEST/skills" "$VENDOR" 2>/dev/null || true; } | wc -l | tr -d ' ')
echo "  vendored: $SKILL_N skills + engine/harness/jit-tooling/domains → .claude/mycelium/"
echo "  rewrote \${CLAUDE_PLUGIN_ROOT} → .claude/mycelium (and /skills/ → .claude/skills/)"
if [ "$RESIDUAL" != "0" ]; then
  echo "  WARNING: $RESIDUAL file(s) still contain an unrewritten \${CLAUDE_PLUGIN_ROOT}/… path — inspect:" >&2
  grep -rlE "$RESIDUAL_RE" "$DEST/skills" "$VENDOR" 2>/dev/null | sed 's/^/    /' >&2
fi
echo "Done. Re-run after a framework upgrade to refresh the vendored snapshot."
