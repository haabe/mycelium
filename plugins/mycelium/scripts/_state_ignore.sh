# shellcheck shell=bash
# Sourced by every Mycelium hook (v0.318.0): when the hook exits, a `.claude/state/` folder with no
# ignore file gets one, so the logs the hooks keep there are never committed by accident in a
# project where /mycelium:setup never ran. See _state_dir.py for why; the rules are in
# state-gitignore.txt, shared with it. Pure bash on purpose: this runs on every hook exit.
#
# It never creates the folder. A hook that wrote nothing leaves nothing behind.
# A hook that needs its own EXIT trap calls mycelium_state_ignore from that trap instead.

_MYCELIUM_STATE_IGNORE_TEMPLATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/state-gitignore.txt"

mycelium_state_ignore() {
  local dir="${CLAUDE_PROJECT_DIR:-.}/.claude/state"
  [ -d "$dir" ] || return 0
  [ -e "$dir/.gitignore" ] && return 0
  [ -f "$_MYCELIUM_STATE_IGNORE_TEMPLATE" ] || return 0
  # noclobber: two hooks racing on a new folder write the file once.
  ( set -C; cat "$_MYCELIUM_STATE_IGNORE_TEMPLATE" > "$dir/.gitignore" ) 2>/dev/null || true
  return 0
}

trap 'mycelium_state_ignore' EXIT
