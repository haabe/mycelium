#!/usr/bin/env bash
# Mycelium next-item-repeat hook (Stop) — v0.188.0, opp-006 sol-006f.
#
# The session-start hook emits ONE item for the human (NEXT ITEM: ... run | rule | snooze | drop)
# and records it in .claude/state/next-item.json. This hook repeats that item ONCE, at the first
# Stop after it was emitted, if nothing has been ruled on it since; then it stays quiet. One
# repeat, not one per turn: the 2026-09-09 discovery's F6 is that every unanswered line is paid
# for by the reader, and a line on every turn is how a reminder gets muted.
#
# Contract: exit 0 silent = nothing to say; exit 0 + JSON systemMessage = the repeat.
# Fail-open and said so: an unreadable state file prints a systemMessage naming it.
# Person override: MYCELIUM_NEXT_ITEM=off.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STATE="$PROJECT_DIR/.claude/state/next-item.json"
LEDGER="$PROJECT_DIR/.claude/state/advisory-ledger.jsonl"

if [ "${MYCELIUM_NEXT_ITEM:-on}" = "off" ] || [ ! -f "$STATE" ]; then
  exit 0
fi

python3 - "$STATE" "$LEDGER" <<'PY'
import json, sys
state_path, ledger_path = sys.argv[1], sys.argv[2]
try:
    st = json.load(open(state_path, encoding="utf-8"))
except Exception as e:  # SPEAKS
    print(json.dumps({"systemMessage": f"Mycelium next-item repeat could not read {state_path} ({type(e).__name__}); the item from session start stands."}))
    sys.exit(0)
if st.get("repeated_at_stop"):
    sys.exit(0)
ruled = False
try:
    for line in open(ledger_path, encoding="utf-8"):
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("kind") == "ruled" and ev.get("id") == st.get("id") and str(ev.get("date", "")) >= str(st.get("emitted_at", "")):
            ruled = True
            break
except OSError:
    pass
st["repeated_at_stop"] = True
try:
    json.dump(st, open(state_path, "w", encoding="utf-8"), ensure_ascii=False)
except OSError:
    pass
if ruled:
    sys.exit(0)
# text_human is the plain, bounded form (0.193.0); older state files carry only "text".
print(json.dumps({"systemMessage": "Still open from session start. " + str(st.get("text_human") or st.get("text", ""))}))
PY
exit 0
