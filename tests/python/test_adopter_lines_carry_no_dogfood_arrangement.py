"""What an adopter reads carries no dogfood-project arrangement (blind read of shipped candidates, 2026-10-11).

WHAT WAS WRONG (the half that remained after 0.319.2 moved release counting to version tags).

1. When five minor releases had shipped since the last recorded cycle, every adopter's session
   start said "a meta-dogfood cycle is owed". Meta-dogfood is the dogfood project's word for its own
   framework cycles; an adopter's releases are their product's.
2. `engine/diamond-rules.md` headed a section "why only two scales have a catalogue door" above a
   paragraph saying no scale has one (v0.301.0), and its lead-in still named L0, L1, L4 and L5 as the
   scales a door might be proposed for.

WHAT THIS PINS. The owed branch of session-start.sh, run in bash with the state it reads, says "a
cycle record is owed" and not "meta-dogfood", and keeps the first clause the advisory ledger keys
on. The diamond-rules heading agrees with the paragraph under it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
HOOK = PLUGIN / "hooks" / "session-start.sh"
RULES = PLUGIN / "engine" / "diamond-rules.md"


def _owed_branch() -> str:
    text = HOOK.read_text(encoding="utf-8")
    m = re.search(r"\n    owed:\*\)\n(.*?)\n      ;;\n", text, re.DOTALL)
    assert m, "could not find the owed:* branch of the cycle-recording case in session-start.sh"
    return m.group(1)


def _run_owed(count: int) -> str:
    script = f'CYCLE_STATE="owed:{count}"; REMINDERS=""\n{_owed_branch()}\nprintf "%s" "$REMINDERS"\n'
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=30,
                          check=True)
    return done.stdout


def test_the_owed_line_says_a_cycle_record_is_owed():
    line = _run_owed(6)
    assert line.startswith("6 minor releases have shipped since the last recorded cycle")
    assert "a cycle record is owed (/mycelium:retrospective)" in line
    assert "meta-dogfood" not in line


def test_the_ledger_still_recognises_the_line():
    source = (PLUGIN / "scripts" / "advisory_ledger.py").read_text(encoding="utf-8")
    pattern = re.search(r'r"(\(\?P<count>\\d\+\) minor releases have shipped since the last '
                        r'recorded cycle)"', source)
    assert pattern, "advisory_ledger.py no longer keys the cycle advisory on its first clause"
    assert re.search(pattern.group(1), _run_owed(7))


def test_the_catalogue_door_heading_agrees_with_its_paragraph():
    text = RULES.read_text(encoding="utf-8")
    heading = next(ln for ln in text.splitlines() if ln.startswith("## What each level RECURS ON"))
    assert "why no scale has a catalogue door" in heading
    assert "only two scales" not in text
    assert "NONE HAS A CATALOGUE DOOR" in text
    assert "proposing a catalogue door for L0, L1, L4 or L5" not in text


def test_the_owed_line_names_no_framework_only_calibration_field():
    """Integration 2026-11-12: the line also said "Effort accuracy is its one required calibration
    field", which holds for a framework-work (meta-dogfood) record only."""
    assert "one required calibration field" not in _run_owed(6)


def test_the_hand_run_check_does_not_name_the_dogfood_class():
    source = (PLUGIN / "scripts" / "check_cycle_recording.py").read_text(encoding="utf-8")
    assert "A `meta-dogfood` cycle is owed" not in source
    assert "A cycle record is owed. Run /mycelium:retrospective" in source
