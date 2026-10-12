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

# THE SAME TEST STANDS IN FRONT OF EVERY BLOCKING PreToolUse COMMAND (0.322.1): the `prefix` line
# of hooks/pretooluse-on-failure.txt, which hooks.json carries before `bash` is started, so that a
# hook that cannot start refuses a call only in a Mycelium project. That prefix must never be
# narrower than this file. Add a marker folder here, or a new way of finding the project, and add
# it there too, or the projects it brings in lose every gate in silence.
# tests/python/test_pretooluse_on_failure.py runs both over one matrix; add the new case to it.

# WHERE MYCELIUM'S OWN FILES ARE (v0.322.3): the folder above this file. That is the plugin's root
# in a plugin install, and the project's `.claude/` only in a legacy install, where the hooks
# themselves were copied into the project. A hook that needs a helper and has no CLAUDE_PLUGIN_ROOT
# (Cursor and Codex do not set it) looks HERE, beside itself. Until 0.322.3 it looked in
# `$PROJECT_DIR/.claude/scripts/` and `.claude/hooks/`, so on those runtimes a repository that
# carried a file by the right name had it run by the hook (blind read round 2, 2026-10-12). No
# hook resolves a script from the project by name any more;
# tests/python/test_hooks_run_only_their_own_scripts.py holds that.
_MYCELIUM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd)"
export _MYCELIUM_ROOT

# A HOOK'S PYTHON NEVER LOOKS IN THE WORKING DIRECTORY (v0.322.4). `python3 -c` and `python3 -`
# put the current directory first on the import path, and a hook's current directory is the
# project. So `import json` in a hook's inline Python loaded `./json.py` when the project had one:
# replayed 2026-10-12 on 0.322.3, four hooks imported planted `json.py`, `yaml.py` and `re.py`.
# A repository could have its code run by the hooks, and an honest project with its own
# `types.py` could crash a gate.
#   - PYTHONSAFEPATH=1 turns that off for every Python 3.11 or later this hook starts, children
#     included.
#   - For the Pythons before it (macOS ships 3.9), the function below hands inline code to
#     scripts/_safe_c.py: a FILE gets its own folder on the path in place of the current one.
# Every hook sources this file on line 2, so no call site changes. A hook that starts an
# interpreter by an explicit path (`"$own" -c ...`) is not covered by the function and must name
# _safe_c.py itself; tests/python/test_hooks_import_nothing_from_the_project.py plants canaries
# for every registered hook and holds both halves.
export PYTHONSAFEPATH=1
_mycelium_py() {  # $1 = the interpreter (a name or a path); the rest = its arguments
  local _bin="$1" _safe="$_MYCELIUM_ROOT/scripts/_safe_c.py"
  shift
  if [ -f "$_safe" ]; then
    case "${1:-}" in
      -c) if [ "$#" -ge 2 ]; then
            local _code="$2"; shift 2
            command "$_bin" "$_safe" "$_code" "$@"; return
          fi;;
      -)  shift; command "$_bin" "$_safe" --stdin "$@"; return;;
    esac
  fi
  command "$_bin" "$@"
}
python3() { _mycelium_py python3 "$@"; }
python() { _mycelium_py python "$@"; }

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
