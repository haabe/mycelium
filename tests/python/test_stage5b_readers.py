"""Every reader of where a diamond is reads its decisions (v0.305.0, phase migration stage 5b).

The next item, the closing path, the purpose-stance check and the stop hook read where a diamond is
through `scale_locks.phase_of`: its decision log first, the recorded phase only without one. Each
test gives a stale `phase` and a decision log that disagree, so a reader still on the field fails.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import check_purpose_stance as ps  # noqa: E402
import derive_closing_path as cp  # noqa: E402
import next_item as ni  # noqa: E402

DEVELOP = [{"decision": d, "on": "2026-10-01"}
           for d in ("set_target", "start_experiment", "commit_to_build")]


def _project(tmp_path: Path, diamonds: list[dict], canvas: dict | None = None) -> Path:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas" / "opportunities.yml").write_text("opportunities: []\n")
    for name, doc in (canvas or {}).items():
        (tmp_path / ".claude" / "canvas" / name).write_text(doc)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": diamonds}))
    return tmp_path


def test_the_next_item_reads_the_decisions():
    stale = {"id": "l3", "scale": "L3", "phase": "discover", "decisions": DEVELOP}
    assert ni._where(stale) == "develop"


def test_the_closing_path_names_the_move_after_the_decisions(tmp_path, capsys):
    d = {"id": "l3", "scale": "L3", "phase": "discover", "confidence": 0.5,
         "decisions": DEVELOP, "theory_gates_status": {"four_risks": "pending"}}
    assert cp.main(["--project-dir", str(_project(tmp_path, [d])), "--diamond-id", "l3"]) == 0
    assert "owed before the next move (develop->deliver)" in capsys.readouterr().out


def test_purpose_stance_reads_where_the_diamond_is():
    stale = {"id": "l3", "scale": "L3", "phase": "discover", "decisions": DEVELOP}
    assert ps._phase_of(stale) == "develop"
    assert ps._phase_of(stale) in ps.BLOCKING_PHASES


def test_the_stop_hook_sees_an_l4_delivering_by_its_decisions(tmp_path):
    l4 = {"id": "l4", "scale": "L4", "phase": "discover",
          "decisions": [*DEVELOP, {"decision": "release", "on": "2026-10-01"}]}
    root = _project(tmp_path, [l4], {"threat-model.yml": "components: []\n"})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root),
           "CLAUDE_PLUGIN_ROOT": str(ROOT / "plugins" / "mycelium")}
    out = subprocess.run(["bash", str(ROOT / "plugins/mycelium/hooks/stop-check.sh")], env=env,
                         input="{}", capture_output=True, text=True, timeout=60, check=False)
    assert "G-S2" in out.stdout + out.stderr, "the L4 is delivering by its decisions"
