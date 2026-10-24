#!/bin/bash
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_prelude.sh" 2>/dev/null || true  # no-op outside a Mycelium project; state ignore file (v0.318.0)
# Mycelium guard-state gate (PreToolUse on Write|Edit|MultiEdit|NotebookEdit, Bash and the
# filesystem MCP writes), v0.281.0
#
# The files that switch a blocking hook off (the ack files, upstream.json, manifest.yml,
# active-execution.json; `_hook_input.GUARD_STATE_REL`) are the user's to write. A write to one asks
# the human in a permission mode where someone is asked, and is refused where nobody would be
# (permissions bypassed, or an automated mode). The three guards that did this before were each
# conditional, so in an ordinary project nothing guarded them; E2E relay on 0.280.0 had the agent
# write its own scale-lock override under bypassed permissions.
#
# Exit 0 always; the decision (ask or deny) is the PreToolUse JSON the helper prints.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
# The verdict below is captured so a refusal reaches the denial ledger (0.316.0), then passed
# through unchanged: same stdout, same exit status.
# shellcheck source=/dev/null
. "$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_fire_log.sh" 2>/dev/null || {
  mycelium_note_refusal() { :; }; mycelium_record_denial() { :; }; }
# Cheap exit: only a call that names a guard-state file, or could remove a marker folder, needs
# python. UNTIL 0.318.3 THIS LISTED THE FILES ONLY, so `rm -rf .claude/canvas .claude/diamonds`
# left here with exit 0 and never reached the helper that asks about it: the removal 0.318.0
# called "the widest off-switch there is" was judged in Python and unreachable from the hook, in
# every permission mode (dogfood harms check 2026-10-11; the tests fed the helper, not this file).
# The second arm is a deliberately loose superset of `_hook_input._REMOVES_MARKER`: a removal verb
# followed by a non-word character, anywhere, in a call that mentions `.claude`. Being loose costs
# one python start on a command like `confirm .claude/x`; being tight is how the first arm missed.
# Third arm (v0.322.6): a Claude Code settings file, where a Mycelium switch can be set
# (scripts/settings_switches.py). Matched by the file's name, in the project or in the home folder.
# Fourth arm (v0.330.0): a subagent's call that names the canvas or the diamonds folder, which only
# the lead agent writes (_hook_input.subagent_write_check). Claude Code puts `agent_id` on the
# payload only for a subagent or in-process teammate, so the main session never takes this arm.
case "$INPUT" in
  *-ack*|*upstream.json*|*manifest.yml*|*active-execution.json*|*move_file*) ;;
  *settings.json*|*settings.local.json*) ;;
  *gitleaks*) ;;  # the scanner's ignore list, its config, an inline allow comment (v0.323.0)
  *'"agent_id"'*canvas*|*'"agent_id"'*diamonds*|*canvas*'"agent_id"'*|*diamonds*'"agent_id"'*) ;;
  *)
    if [[ "$INPUT" == *.claude* && "$INPUT" =~ (rm|rmdir|mv)[^A-Za-z0-9_] ]]; then :; else exit 0; fi ;;
esac
HELPER="$(dirname "${BASH_SOURCE[0]}")/../scripts/_hook_input.py"
[ -f "$HELPER" ] || HELPER="${CLAUDE_PLUGIN_ROOT:-}/scripts/_hook_input.py"
OUT=$(printf '%s' "$INPUT" | python3 "$HELPER" --project-dir "$PROJECT_DIR" --guard-state guard-state-gate)
mycelium_note_refusal "$OUT" 0
[ -n "$OUT" ] && printf '%s\n' "$OUT"
exit 0
