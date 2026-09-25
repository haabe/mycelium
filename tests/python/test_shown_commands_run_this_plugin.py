"""The commands Mycelium shows run THIS plugin's copy of the script (v0.258.0).

E2E run 32: the next item said `advisory_ledger.py rule ...` with no path. The agent ran
`find . ~/.claude/plugins -name advisory_ledger.py | head -1`, got plugin cache 0.220.0 (37 versions
old, no MYCELIUM_TODAY), and recorded the founder's answer with a date before the question; the
answer never counted and the item escalated for sessions after it was answered. It also recorded
"not before Monday ... ask me again after Wednesday" as a bare `keep`, losing the condition.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
_spec = importlib.util.spec_from_file_location("next_item_paths", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(SCRIPTS))
_spec.loader.exec_module(ni)

OWN = str((SCRIPTS / "advisory_ledger.py").resolve())


def _item() -> dict:
    return {"id": "deliver-l3:d-004", "text": "d-004 (L3) has built what its test needs.",
            "command": "/mycelium:diamond-progress d-004", "shown": 5,
            "first_shown": "2026-09-30"}


def test_the_shown_command_names_this_plugins_own_script():
    line = ni.render(_item())
    assert f'python3 "{OWN}" rule --id deliver-l3:d-004' in line
    assert "`advisory_ledger.py" not in line, "a bare name makes the agent search for a copy"


def test_the_muted_advisory_line_names_this_plugins_own_script():
    src = (SCRIPTS / "advisory_ledger.py").read_text()
    assert 'muted until you rule (python3 "{Path(__file__).resolve()}" rule' in src


def test_the_answer_prompts_say_which_ruling_fits_which_answer(tmp_path):
    state = tmp_path / ni.STATE_REL
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"id": "deliver-l3:d-004", "shown": 5, "session": "s1",
                                 "first_shown": "2026-09-30", "emitted_at": "2026-09-30",
                                 "text_human": "d-004 (L3) has built what its test needs"}))
    answer = ni.answer_line(tmp_path, "not now, ask me again after Wednesday's check")
    assert f'python3 "{OWN}"' in answer and '--until asked --note "X"' in answer
    nudge = ni.prompt_line(tmp_path)
    assert f'python3 "{OWN}"' in nudge and '--until asked --note "X"' in nudge


def test_running_the_shown_command_records_the_answer_with_the_in_world_date(tmp_path):
    """Copy the command as shown, run it: this plugin's script, today's date from the harness, the
    condition kept in the note."""
    shown = re.search(r"`(python3 \"[^\"]+\" rule --id \S+)", ni.render(_item())).group(1)
    cmd = (f'{shown} --ruling snooze --until asked --note "after Wednesday\'s check" '
           f'--project-dir "{tmp_path}"')
    env = {"MYCELIUM_TODAY": "2026-10-04",
           "PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}
    subprocess.run(shlex.split(cmd), check=True, env=env, capture_output=True, text=True)
    rows = [json.loads(x) for x in
            (tmp_path / ".claude" / "state" / "advisory-ledger.jsonl").read_text().splitlines()]
    ruled = [r for r in rows if r.get("kind") == "ruled"][-1]
    assert ruled["date"] == "2026-10-04", "the in-world date, not the machine's"
    assert ruled["until"] == "asked" and ruled["note"] == "after Wednesday's check"
