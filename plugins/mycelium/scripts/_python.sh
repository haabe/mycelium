# shellcheck shell=bash
# Mycelium's python for the safety gates (v0.290.0). Sourced, never run.
#
# The gates read YAML, so they need a python3 with PyYAML. Claude Code installs a plugin's Node
# dependencies but not its Python ones, and documents ${CLAUDE_PLUGIN_DATA} as the place for a
# plugin's installed dependencies (kept across updates, removed on uninstall). So, in order:
#   1. the python3 on PATH, if it imports yaml (most machines that have used Python);
#   2. Mycelium's own environment, ${CLAUDE_PLUGIN_DATA}/pyenv, which /mycelium:setup creates on
#      request, pinned to the PyYAML version CI uses;
#   3. the python3 on PATH anyway: scale_locks.py then exits 3 ("cannot check") and each safety
#      gate REFUSES a build or a release, saying how to fix it. Before 0.290.0 they allowed it.
# Nothing here installs anything: installing happens only when the user runs /mycelium:setup.

mycelium_python() {
  if python3 -c 'import yaml' >/dev/null 2>&1; then
    printf 'python3'
    return 0
  fi
  local own="${CLAUDE_PLUGIN_DATA:-}/pyenv/bin/python"
  if [ -n "${CLAUDE_PLUGIN_DATA:-}" ] && [ -x "$own" ] && "$own" -c 'import yaml' >/dev/null 2>&1; then
    printf '%s' "$own"
    return 0
  fi
  printf 'python3'
}

# The line a gate prints when it refuses because it cannot read the locks.
# shellcheck disable=SC2034  # read by the gates that source this file
MYCELIUM_NO_YAML_FIX="PyYAML is not available to Mycelium, so readiness cannot be checked and this is refused rather than let through. Run /mycelium:setup (it installs PyYAML for Mycelium only, in the plugin's own data directory), or install it for your python3 (pip3 install pyyaml), then retry."
