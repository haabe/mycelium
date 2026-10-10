# shellcheck shell=bash
# Sourced on the first line of every Mycelium hook (v0.318.0). Two jobs, decided once here.
#
# 1. NOT A MYCELIUM PROJECT: DO NOTHING. A project uses Mycelium when it has `.claude/canvas/` or
#    `.claude/diamonds/` (what /mycelium:setup and /mycelium:start create). Anywhere else the hook
#    exits 0 at once: no gate, no output, no log, nothing written in the project. Founder ruling
#    2026-10-10, after Anthropic's plugin directory review of v0.317.4 found the hooks logging in
#    every repo the plugin ran in. `.claude/state/` is NOT the signal: versions before 0.318.0
#    created it in every repo. The one write is outside the project: a timestamp in the user's
#    temp folder, so the entry skills can still tell "hooks ran" from "hooks are off" (Codex CLI
#    runs none until trusted) before the project has any state.
#    A script in hooks/ that is not a hook (install-runtime-hooks.sh) sets
#    MYCELIUM_PRELUDE_ANY_PROJECT=1 before sourcing this.
#
# 2. THE STATE FOLDER NEVER LACKS ITS IGNORE FILE. When the hook exits and `.claude/state/` exists
#    without `.gitignore`, it gets one from state-gitignore.txt (shared with _state_dir.py). It
#    never creates the folder, never rewrites an existing file, writes nothing to stdout and
#    leaves the exit status alone. A hook that needs its own EXIT trap calls
#    mycelium_state_ignore from it.
#
# Pure bash on purpose: this runs on every hook call.

_mycelium_is_project() { [ -d "$1/.claude/canvas" ] || [ -d "$1/.claude/diamonds" ]; }

# Which project. Claude Code sets CLAUDE_PROJECT_DIR; Codex CLI does not, and a session may start in
# a subfolder, so then walk up from here to the nearest folder that is a Mycelium project, as
# preflight.sh does, and export it so every hook and helper agrees on one root.
if [ -z "${CLAUDE_PROJECT_DIR:-}" ]; then
  _mycelium_d="$PWD"
  while [ -n "$_mycelium_d" ] && [ "$_mycelium_d" != "/" ]; do
    if _mycelium_is_project "$_mycelium_d"; then export CLAUDE_PROJECT_DIR="$_mycelium_d"; break; fi
    _mycelium_d="$(dirname "$_mycelium_d")"
  done
fi

if [ "${MYCELIUM_PRELUDE_ANY_PROJECT:-}" != "1" ] && ! _mycelium_is_project "${CLAUDE_PROJECT_DIR:-.}"; then
  touch "${TMPDIR:-/tmp}/mycelium-hooks-alive-$(id -u 2>/dev/null || echo 0)" 2>/dev/null || true
  # Read the payload before leaving, bounded as in preflight.sh (a shell-tool heredoc gives a
  # stdin that never ends), so the caller never writes into a closed pipe.
  if [ ! -t 0 ]; then IFS= read -r -d '' -t 3 _ || true; fi
  exit 0
fi

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
