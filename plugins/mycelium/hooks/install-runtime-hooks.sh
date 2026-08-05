#!/usr/bin/env bash
# Generate a runtime's hook manifest with this plugin's REAL path baked in.
#
# WHY THIS EXISTS. A plugin cannot know where it is installed, so it must not
# ship a path. hooks.codex.json and hooks.cursor.json used to carry
# `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/cache/mycelium-plugin/mycelium}`
# — a hardcoded guess that was wrong twice over: the marketplace directory is
# `haabe-mycelium`, not `mycelium-plugin`, and the cache is VERSIONED
# (`.../mycelium/0.87.0/`), so no unversioned literal can ever resolve. Codex
# and Cursor do not set CLAUDE_PLUGIN_ROOT — Cursor exports CLAUDE_PROJECT_DIR
# instead — so the fallback branch was the LIVE path for every consumer of
# those manifests, and it resolved to a file that does not exist.
#
# The failure was silent and it failed OPEN. `bash /missing/path/gate.sh` exits
# 127. The hook contract blocks on exit 2. So every gate reported "not blocked"
# while never having run. Five more commands carried a bare
# `${CLAUDE_PLUGIN_ROOT}` with no fallback at all, expanding to an empty root.
#
# It also closes the gap hooks/README.md has recorded as open since v0.85.0:
# "whether anything copies it to a path Cursor reads is unknown from inside
# this repository. If nothing does, Cursor consumers get no Mycelium hooks at
# all." This is the thing that copies it.
#
# WHAT IT REFUSES TO DO. It never writes a manifest it cannot prove is wired:
# the placeholder must be gone AND every hook script named in the output must
# exist on disk. A generated file pointing at absent scripts would reproduce
# the exact defect this replaces, one layer down.
#
# Usage:
#   bash install-runtime-hooks.sh cursor [project-root]
#   bash install-runtime-hooks.sh codex  [project-root]
#
# Re-run after every plugin upgrade: the resolved path contains the version.

set -euo pipefail

PLACEHOLDER="__MYCELIUM_PLUGIN_ROOT__"

die() { echo "ERROR: $*" >&2; exit 1; }

RUNTIME="${1:-}"
case "$RUNTIME" in
  cursor) TARGET_DIR=".cursor" ;;
  codex)  TARGET_DIR=".codex" ;;
  "")     die "no runtime given. Usage: install-runtime-hooks.sh <cursor|codex> [project-root]" ;;
  *)      die "unknown runtime '$RUNTIME'. Expected 'cursor' or 'codex'." ;;
esac

# Resolve the plugin root. Env first (Claude Code, or an explicit override),
# then self-location — this script lives at <plugin_root>/hooks/, so its own
# path is authoritative for a git clone or any other layout. There is
# deliberately NO third branch: a guessed path is what this script replaces.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}/hooks" ]; then
  PLUGIN_ROOT="$(cd "$CLAUDE_PLUGIN_ROOT" && pwd)"
elif [ -d "$SCRIPT_DIR/../hooks" ]; then
  PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  die "cannot locate the Mycelium plugin root. Run this script from its
  installed location (<plugin_root>/hooks/install-runtime-hooks.sh), or export
  CLAUDE_PLUGIN_ROOT to the directory containing hooks/."
fi

SOURCE="$PLUGIN_ROOT/hooks/hooks.$RUNTIME.json"
[ -f "$SOURCE" ] || die "no manifest at $SOURCE"

PROJECT_ROOT="${2:-$PWD}"
[ -d "$PROJECT_ROOT" ] || die "project root '$PROJECT_ROOT' is not a directory"
TARGET="$PROJECT_ROOT/$TARGET_DIR/hooks.json"

# Never clobber a hooks.json this script did not write. A user's own Cursor
# hooks are theirs; silently replacing them would be a worse failure than the
# one being fixed.
if [ -f "$TARGET" ] && ! grep -q "mycelium" "$TARGET" 2>/dev/null; then
  die "$TARGET already exists and does not look like a Mycelium manifest.
  Move it aside, or merge by hand — this script will not overwrite it."
fi

mkdir -p "$PROJECT_ROOT/$TARGET_DIR"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# The substitution. `|` as the sed delimiter because the path contains `/`.
sed "s|$PLACEHOLDER|$PLUGIN_ROOT|g" "$SOURCE" > "$TMP"

# PROOF, not assumption. Two checks, both of which the old hardcoded fallback
# would have failed.
if grep -q "$PLACEHOLDER" "$TMP"; then
  die "substitution did not take — $PLACEHOLDER still present in the output"
fi

missing=""
while IFS= read -r script; do
  [ -f "$script" ] || missing="$missing
  $script"
done < <(grep -o "$PLUGIN_ROOT/hooks/[A-Za-z0-9_-]*\.sh" "$TMP" | sort -u)

if [ -n "$missing" ]; then
  die "the generated manifest names hook scripts that do not exist:$missing
  This means the resolved plugin root ($PLUGIN_ROOT) is wrong. Refusing to
  write a manifest whose hooks would exit 127 and silently fail open."
fi

mv "$TMP" "$TARGET"
trap - EXIT

count="$(grep -c "$PLUGIN_ROOT/hooks/" "$TARGET" || true)"
echo "Wrote $TARGET"
echo "  plugin root: $PLUGIN_ROOT"
echo "  $count hook command(s), every referenced script verified present"
echo
echo "Re-run this after upgrading the plugin — the resolved path carries the version."
