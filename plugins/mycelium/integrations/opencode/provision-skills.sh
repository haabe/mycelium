#!/usr/bin/env bash
#
# Mycelium → opencode skill provisioner (project-local vendoring).
#
# WHY: opencode discovers skills natively (reads .claude/skills/) but does NO
# ${...} interpolation of skill content, and its read tool treats a literal
# ${CLAUDE_PLUGIN_ROOT}/... path as project-relative → fails. 36 of 55 skills
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

# 4. Report.
SKILL_N=$(find "$DEST/skills" -name 'SKILL.md' | wc -l | tr -d ' ')
RESIDUAL=$(grep -rl 'CLAUDE_PLUGIN_ROOT' "$DEST/skills" "$VENDOR" 2>/dev/null | wc -l | tr -d ' ')
echo "  vendored: $SKILL_N skills + engine/harness/jit-tooling/domains → .claude/mycelium/"
echo "  rewrote \${CLAUDE_PLUGIN_ROOT} → .claude/mycelium (and /skills/ → .claude/skills/)"
if [ "$RESIDUAL" != "0" ]; then
  echo "  WARNING: $RESIDUAL file(s) still contain a literal CLAUDE_PLUGIN_ROOT — inspect:" >&2
  grep -rl 'CLAUDE_PLUGIN_ROOT' "$DEST/skills" "$VENDOR" 2>/dev/null | sed 's/^/    /' >&2
fi
echo "Done. Re-run after a framework upgrade to refresh the vendored snapshot."
