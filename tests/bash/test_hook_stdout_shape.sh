#!/usr/bin/env bash
# tests/bash/test_hook_stdout_shape.sh
# Runs EVERY command registered in hooks/hooks.json once, against a representative
# stdin payload in an empty project, and asserts the shape of what reaches stdout:
# empty, plain text that does not open with a brace, or JSON that parses.
#
# WHY: Claude Code 2.1.248 reports brace-led stdout that is not valid JSON as a hook
# error where it used to show it as text. A static grep for hand-built JSON cannot
# see a heredoc, a cat, or what a child script prints; only running the hook can.
# The list comes from hooks.json, so a hook registered later is covered by
# definition and a hook that is not registered is not claimed.
#
# WHAT THIS DOES NOT COVER: one payload per registration in an EMPTY project. A
# branch that only fires on a populated canvas is exercised by that hook's own test
# file, which should call assert_stdout_json_or_text on what it captures.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_assert.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLUGIN_ROOT="$REPO_ROOT/plugins/mycelium"

test_every_registered_hook_emits_json_or_text() {
    local tmp; tmp=$(mktemp -d)
    local outdir; outdir=$(mktemp -d)
    mkdir -p "$tmp/.claude/state" "$tmp/src"
    # The driver runs each registration with a hard timeout and writes one stdout
    # file per run. Judging the shape stays in the shared bash assertion.
    python3 - "$PLUGIN_ROOT" "$tmp" "$outdir" <<'PYEOF'
import json, os, subprocess, sys
plugin_root, proj, outdir = sys.argv[1:4]
reg = json.load(open(os.path.join(plugin_root, 'hooks', 'hooks.json')))['hooks']

def payload(event, matcher):
    base = {'hook_event_name': event, 'session_id': 'stdout-shape-test', 'cwd': proj}
    first = (matcher or '').split('|')[0]
    if event in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure'):
        if first == 'Bash':
            base.update(tool_name='Bash', tool_input={'command': 'ls'})
        elif first.startswith('mcp__filesystem__'):
            base.update(tool_name='mcp__filesystem__write_file',
                        tool_input={'path': os.path.join(proj, 'src', 'a.py'), 'content': 'x = 1\n'})
        elif first == 'WebSearch':
            base.update(tool_name='WebSearch', tool_input={'query': 'anything'})
        elif first == 'Read':
            base.update(tool_name='Read', tool_input={'file_path': os.path.join(proj, 'src', 'a.py')})
        else:
            base.update(tool_name='Write',
                        tool_input={'file_path': os.path.join(proj, 'src', 'a.py'), 'content': 'x = 1\n'})
        if event != 'PreToolUse':
            base['tool_response'] = {'stdout': '', 'stderr': 'boom', 'exit_code': 1}
    elif event == 'SessionStart':
        base['source'] = 'startup'
    elif event == 'UserPromptSubmit':
        base['prompt'] = 'add a login page'
    return json.dumps(base)

env = dict(os.environ, CLAUDE_PLUGIN_ROOT=plugin_root, CLAUDE_PROJECT_DIR=proj,
           MYCELIUM_TEST='1', GH_TOKEN='', GITHUB_TOKEN='')
n = 0
for event, groups in reg.items():
    for g in groups:
        for h in g['hooks']:
            cmd = h['command']
            # --async detaches a background worker by design; its stdout is not a hook response.
            if '--async' in cmd:
                continue
            n += 1
            name = '%02d__%s__%s' % (n, event, os.path.basename(cmd.split()[1]) + ''.join(cmd.split()[2:]))
            try:
                r = subprocess.run(cmd.replace('${CLAUDE_PLUGIN_ROOT}', plugin_root), shell=True,
                                   input=payload(event, g.get('matcher')), capture_output=True,
                                   text=True, timeout=60, env=env, cwd=proj)
                out = r.stdout
            except subprocess.TimeoutExpired:
                out = '{TIMEOUT after 60s: not JSON on purpose, so the assertion fails loudly'
            open(os.path.join(outdir, name), 'w').write(out)
print(n)
PYEOF
    local count=0 f
    for f in "$outdir"/*; do
        [ -f "$f" ] || continue
        count=$((count + 1))
        assert_stdout_json_or_text "$(cat "$f")" "$(basename "$f")"
    done
    rm -rf "$tmp" "$outdir"
    # A driver that enumerated nothing would pass every assertion it never made.
    if [ "$count" -ge 30 ]; then
        assert_eq "ok" "ok" "covered $count registrations from hooks.json"
    else
        assert_eq "$count" ">=30" "registrations covered (hooks.json enumerates ~38; a low count means the driver broke)"
    fi
}

run_test test_every_registered_hook_emits_json_or_text

report
