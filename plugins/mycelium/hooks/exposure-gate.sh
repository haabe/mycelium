#!/bin/bash
# Mycelium exposure gate (PreToolUse on Bash)
#
# Blocks a command that puts the work in front of real people (a deploy CLI's deploy verb, a
# package publish, a remote shell or copy that pulls, restarts or syncs onto a host) while no
# delivery cycle is ready for it: an open L3, L4 or L5 whose chain holds, in Deliver, with
# Security, Privacy and Service Quality passed (v0.246.0; scripts/scale_locks.py --exposure-hook).
#
# Provenance: E2E dogfood run 10 on 0.245.0. An SMS swap app holding staff phone numbers and
# private link tokens went live at one site and was being rolled out to a second, under an L3
# still in define with every gate pending: no threat model, no privacy assessment. The matrix
# requires Security and Privacy at L3, but at phase transitions, and the phase never moved. The
# founder: "Even a prototype should follow best practices, even if it is only a pilot. Anything
# user facing collecting data of any sorts can wreck havoc if there are holes that allows
# strangers on the inside or leak data out."
#
# Scope is deliberately narrow:
#   - Bash only, and only commands matching a short deploy/publish list; everything else exits
#     before python starts. `git push origin`, `ssh host tail`, local rsync and `docker compose up`
#     are not deploys and pass.
#   - A project with no diamonds at all is not judged here.
#   - A deploy the USER runs cannot be seen by any hook; the operating contract and /preflight
#     carry the rule for that case.
#   - Escape hatch: .claude/state/delivery-skip-ack (the user declared the work untracked).
#
# Exit 0 = allow, Exit 2 = block (stderr is shown to the agent).

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
INPUT=$(cat)
shopt -s nocasematch
case "$INPUT" in
  *deploy*|*publish*|*push*|*apply*|*helm*|*rollout*|*image*|*ssh*|*scp*|*rsync*|*upload*|*pulumi*|*sync*|*function-code*) ;;
  *) exit 0 ;;
esac
shopt -u nocasematch
[ -f "$PROJECT_DIR/.claude/state/delivery-skip-ack" ] && exit 0
LOCKS="$(dirname "${BASH_SOURCE[0]}")/../scripts/scale_locks.py"
[ -f "$LOCKS" ] || LOCKS="${CLAUDE_PLUGIN_ROOT:-}/scripts/scale_locks.py"
printf '%s' "$INPUT" | python3 "$LOCKS" --project-dir "$PROJECT_DIR" --exposure-hook
rc=$?
# 0 = allowed, 3 = PyYAML missing (hooks/preflight.sh says the locks are unchecked, every prompt).
# Anything else refuses, including a crash, whose traceback is on stderr.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/exposure-gate-fires.jsonl" "blocked" 2>/dev/null || true
  exit 2
fi
exit 0
