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
  *ngrok*|*cloudflared*|*localtunnel*|*tailscale*|*"lt --port"*) ;;  # tunnels (v0.290.0)
  *) exit 0 ;;
esac
shopt -u nocasematch
LOCKS="$(dirname "${BASH_SOURCE[0]}")/../scripts/scale_locks.py"
[ -f "$LOCKS" ] || LOCKS="${CLAUDE_PLUGIN_ROOT:-}/scripts/scale_locks.py"
# shellcheck source=../scripts/_python.sh
. "$(dirname "$LOCKS")/_python.sh"  # mycelium_python, mycelium_skip_ack and the fix line
# The user's skip-ack lifts a release only when it says `releases: true`, and only while it is in
# date (v0.293.0). Until then the file's mere existence lifted every release, forever.
mycelium_skip_ack release && exit 0
printf '%s' "$INPUT" | "$(mycelium_python)" "$LOCKS" --project-dir "$PROJECT_DIR" --exposure-hook
rc=${PIPESTATUS[1]}
# 0 = allowed. 3 = PyYAML missing: since 0.290.0 that REFUSES too, with the fix, because this
# command matched a release and nothing could check that the work is ready for real people.
# Anything else refuses, including a crash, whose traceback is on stderr.
if [ "$rc" -eq 3 ]; then
  printf 'Mycelium exposure gate: this command looks like a release. %s\n' "$MYCELIUM_NO_YAML_FIX" >&2
  rc=2
fi
if [ "$rc" -ne 0 ]; then
  . "${CLAUDE_PLUGIN_ROOT:-$(dirname "${BASH_SOURCE[0]}")/..}/scripts/_hook_fire_log.sh" 2>/dev/null || true
  mycelium_log_fire ".claude/state/exposure-gate-fires.jsonl" "blocked" 2>/dev/null || true
  exit 2
fi
exit 0
