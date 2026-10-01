"""A recorded decision stays recorded (v0.309.1, founder ruling DL-1374, enforcing DL-1373).

DL-1373 ruled that a loop iterates by appending decisions, never by editing them, and shipped no
code: a repeated decision is not a move, so appending needed none. Tested on 0.308.2 through every
Write/Edit hook, removing `commit_to_build` also passed and moved the diamond back to "target set".
The scale-lock gate now refuses a write that removes a recorded decision or changes its name or
date; notes, gates and rulings stay editable, and a date never recorded may be filled in."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
import scale_locks as sl  # noqa: E402

REWRITE = "rewrites its recorded decisions"
L3 = {"id": "l3-a", "scale": "L3", "name": "a test",
      "theory_gates_status": {"evidence": "pass", "cynefin": "pass", "bias": "pass",
                              "corrections": "pass"},
      "decisions": [{"decision": "set_target", "on": "2026-09-01"},
                    {"decision": "start_experiment", "on": "2026-09-02", "note": "a concierge"},
                    {"decision": "commit_to_build", "on": "2026-09-02"}]}


def _doc(*diamonds, **lists):
    return yaml.safe_dump({"active_diamonds": list(diamonds), **lists}, sort_keys=False)


def _judge(tmp_path, after: str) -> list[str]:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True, exist_ok=True)
    return sl.violations_between(str(tmp_path), _doc(L3), after)


def _with(decisions):
    return {**copy.deepcopy(L3), "decisions": decisions}


def _rewrites(found):
    return [x for x in found if REWRITE in x]


def test_removing_a_decision_is_refused_with_the_way_forward(tmp_path):
    out = _rewrites(_judge(tmp_path, _doc(_with(L3["decisions"][:2]))))
    assert len(out) == 1, out
    assert "`commit_to_build` (2026-09-02) is gone" in out[0]
    assert "another `start_experiment`" in out[0] and "appending" in out[0]


def test_renaming_redating_or_reordering_a_decision_is_refused(tmp_path):
    d = copy.deepcopy(L3["decisions"])
    renamed = [d[0], {**d[1], "decision": "commit_to_build"}, d[2]]
    redated = [d[0], {**d[1], "on": "2026-09-05"}, d[2]]
    reordered = [d[1], d[0], d[2]]
    for decisions, said in ((renamed, "became `commit_to_build`"),
                            (redated, "moved from 2026-09-02 to 2026-09-05"),
                            (reordered, "`set_target` (2026-09-01) became `start_experiment`")):
        out = _rewrites(_judge(tmp_path, _doc(_with(decisions))))
        assert out and said in out[0], (said, out)


def test_appending_and_editing_what_may_change_pass(tmp_path):
    """The controls: DL-1373's iteration, and the fields DL-1374 leaves editable."""
    d = copy.deepcopy(L3["decisions"])
    appended = [*d, {"decision": "start_experiment", "on": "2026-09-10",
                     "note": "a second test: the first read inconclusive"}]
    edited = [d[0], {**d[1], "note": "a concierge with three clients", "ruling": "progressed",
                     "gates": {"evidence": "pass"}}, d[2]]
    for decisions in (appended, edited):
        assert not _rewrites(_judge(tmp_path, _doc(_with(decisions))))


def test_a_date_never_recorded_may_be_filled_in(tmp_path):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    undated = _with([{"decision": "set_target", "on": None, "reconstructed": True}])
    dated = _with([{"decision": "set_target", "on": "2026-09-01", "reconstructed": True}])
    assert not _rewrites(sl.violations_between(str(tmp_path), _doc(undated), _doc(dated)))


def test_a_diamond_moved_to_another_list_keeps_its_record(tmp_path):
    kept = _judge(tmp_path, _doc(killed_diamonds=[copy.deepcopy(L3)]))
    assert not _rewrites(kept)
    lost = _judge(tmp_path, _doc(killed_diamonds=[_with(L3["decisions"][:1])]))
    assert _rewrites(lost), "killing a diamond does not erase what it decided"


def test_the_hook_refuses_a_removed_decision(tmp_path):
    """Through hooks/scale-lock-gate.sh, as the agent's Write reaches it (a function test passing
    while the hook never called the function is a failure this project has had)."""
    active = tmp_path / ".claude" / "diamonds" / "active.yml"
    active.parent.mkdir(parents=True)
    (tmp_path / ".claude" / "state").mkdir()
    active.write_text(_doc(L3))
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}

    def gate(content: str) -> tuple[int, str]:
        payload = {"tool_name": "Write", "tool_input": {"file_path": str(active),
                                                        "content": content}}
        r = subprocess.run(["bash", str(PLUGIN / "hooks" / "scale-lock-gate.sh")],
                           input=json.dumps(payload), capture_output=True, text=True, env=env,
                           timeout=60, check=False)
        return r.returncode, r.stderr

    rc, err = gate(_doc(_with(L3["decisions"][:2])))
    assert rc == 2 and REWRITE in err, err
    rc, err = gate(_doc(_with([*L3["decisions"], {"decision": "start_experiment",
                                                  "on": "2026-09-10"}])))
    assert rc == 0, err
