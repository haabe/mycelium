"""Readers keyed to decisions, not phase moves (v0.299.0, phase migration stage 3b-2).

The closing path says what each pending gate is owed before: the next move's decisions, anyone
outside the team meeting the work, or a later move. The purpose-stance check blocks once a diamond
has decided to build (founder ruling e), read from the decision table.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import check_purpose_stance as ps  # noqa: E402
import derive_closing_path as cp  # noqa: E402
import scale_locks as sl  # noqa: E402
from decided import decided, decided_text  # noqa: E402

L3 = """active_diamonds:
- id: l3
  scale: L3
  phase: develop
  confidence: 0.6
  theory_gates_status:
    four_risks: pending
    bias: pass-with-risk
    bvssh: pending
"""


def _out(tmp_path, capsys, active=L3):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(decided_text(active))
    (tmp_path / ".claude" / "canvas" / "opportunities.yml").write_text("opportunities: []\n")
    assert cp.main(["--project-dir", str(tmp_path), "--diamond-id", "l3"]) == 0
    return capsys.readouterr().out


def _group(out: str, heading: str) -> list[str]:
    lines = out.splitlines()
    start = next(i for i, x in enumerate(lines) if x.startswith(heading))
    rows = []
    for x in lines[start + 1:]:
        if x.endswith(":") or " | " not in x:
            break
        rows.append(x.split(" ", 1)[0])
    return rows


def test_the_closing_path_says_what_each_gate_is_owed_before(tmp_path, capsys):
    out = _out(tmp_path, capsys)
    assert "owed before the next move (develop->deliver), which decides: release:" in out
    owed = _group(out, "owed before the next move")
    assert "four_risks" in owed and "evidence" in owed
    safety = _group(out, "safety gates the next move")
    assert {"security", "privacy", "service_quality", "regulatory"} <= set(safety)
    assert _group(out, "not passed, and not needed for the next move") == ["bvssh"]
    assert _group(out, "passed with a risk recorded") == ["bias"]


def test_define_to_develop_names_both_its_decisions(tmp_path, capsys):
    out = _out(tmp_path, capsys, L3.replace("phase: develop", "phase: define"))
    assert "which decides: start experiment and commit to build" in out


def test_purpose_stance_blocks_once_the_diamond_decides_to_build():
    assert sl.phases_after("commit_to_build") == ("develop", "deliver", "complete")
    assert ps.BLOCKING_PHASES == ("develop", "deliver")
    assert sl.phases_after("set_target") == ("define", "develop", "deliver", "complete")
    assert sl.phases_after("no_such_decision") == ()
