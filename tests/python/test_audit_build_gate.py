"""The build gate, from the 2026-10-01 control audit (DL-1370, batch 2: P10-P14). Each gap was
reproduced on 0.307.5 before it was fixed.

The founder's rule on controls (2026-10-01): the record each test is about (the ack's scope, the
solution an L4 names, `close`) is written here explicitly. The ladder ABOVE the diamond under test
(L0-L2) comes from the suite's fixture and its phase conversion, which supplies none of those.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402

DEFINED = [{"decision": "set_target", "on": "2026-09-20"}]
DEVELOP = [*DEFINED, *({"decision": d, "on": "2026-09-21"}
                       for d in ("start_experiment", "commit_to_build"))]
RELEASED = [*DEVELOP, {"decision": "release", "on": "2026-09-22"}]


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _project(tmp_path: Path, diamonds: list[dict], **kw) -> Path:
    return Path(tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(),
                             diamonds=diamonds, **kw))


def _gate(p: Path, payload: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env.update(CLAUDE_PROJECT_DIR=str(p), CLAUDE_PLUGIN_ROOT=str(PLUGIN))
    return subprocess.run(["bash", str(PLUGIN / "hooks" / "discovery-gate.sh")], env=env,
                          input=json.dumps(payload), text=True, capture_output=True, timeout=60,
                          check=False)


def _write(p: Path, rel: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": str(p / rel), "content": "x = 1\n"}}


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


NOT_READY = {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "decisions": DEFINED}


# P10 ------------------------------------------------------------------------------------------

def test_a_discovery_ack_does_not_lift_the_delivery_gate_once_discovery_is_under_way(tmp_path):
    """P10: the ack a user writes when declining discovery on a cold project lifted the whole gate
    for good, the delivery stage included, after the project started discovery."""
    p = _project(tmp_path, [NOT_READY])
    assert _gate(p, _write(p, "app/main.py")).returncode == 2, "control: refused without an ack"
    (p / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    (p / ".claude" / "state" / "discovery-skip-ack").write_text("2026-07-02: just build it\n")
    assert _gate(p, _write(p, "app/main.py")).returncode == 2


def test_control_a_discovery_ack_still_lifts_the_cold_project_gate(tmp_path):
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir()  # setup ran, discovery did not (v0.318.0 prelude)
    assert _gate(tmp_path, _write(tmp_path, "app/main.py")).returncode == 2
    (tmp_path / ".claude" / "state" / "discovery-skip-ack").write_text("2026-07-02: just build\n")
    assert _gate(tmp_path, _write(tmp_path, "app/main.py")).returncode == 0


# P11 ------------------------------------------------------------------------------------------

def _scoped_ack(p: Path) -> None:
    (p / ".claude" / "state").mkdir(parents=True, exist_ok=True)
    (p / ".claude" / "state" / "delivery-skip-ack").write_text(
        "recorded_at: 2026-09-24\nexpires: 2026-10-24\ncovers: [prototypes/]\nwhy: spike only\n")


def test_a_scoped_ack_covers_every_file_a_command_writes_or_none(tmp_path):
    """P11: the ack was checked against the first gated file a shell command wrote."""
    p = _project(tmp_path, [NOT_READY])
    _scoped_ack(p)
    both = _bash("printf 'x' > prototypes/a.py; printf 'y' > app/b.py")
    assert _gate(p, both).returncode == 2
    assert _gate(p, _bash("printf 'x' > prototypes/a.py")).returncode == 0, "control: covered"


def test_a_declared_prototype_frees_only_itself(tmp_path):
    """P11's twin: the declared-prototype exemption also read only the first file."""
    p = _project(tmp_path, [NOT_READY])
    active = p / ".claude" / "diamonds" / "active.yml"
    doc = yaml.safe_load(active.read_text())
    doc["prototype_paths"] = ["prototypes/"]
    active.write_text(yaml.safe_dump(doc))
    both = _bash("printf 'x' > prototypes/a.py; printf 'y' > app/b.py")
    assert _gate(p, both).returncode == 2
    assert _gate(p, _bash("printf 'x' > prototypes/a.py")).returncode == 0, "control: a prototype"


# P12 ------------------------------------------------------------------------------------------

SET = [{"id": "sol-001", "name": "Backup approver",
        "riskiest_assumption": {"statement": "a backup approves", "cheapest_test": "a trial",
                                "verdict": "validated"},
        "provenance": {"evidence_type": "test-validated"}},
       {"id": "sol-002", "name": "Shift board"}]


def _set_project(tmp_path: Path, l4_ref: str | None, ack: str | None = None) -> str:
    opps = tsl._full_opps()
    opps["opportunities"][0]["solutions"] = SET
    l3 = {"id": "l3-a", "scale": "L3", "object_ref": "opp-001", "decisions": RELEASED,
          "theory_gates_status": dict(tsl.EXPOSE_PASSED), "exposures": [dict(tsl.RECORD)]}
    l4 = {"id": "l4-a", "scale": "L4", "parent": "l3-a", "decisions": DEVELOP,
          "theory_gates_status": dict(tsl.BUILD_PASSED)}
    if l4_ref:
        l4["object_ref"] = l4_ref
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=opps, diamonds=[l3, l4], ack=ack)


def test_an_l4_on_a_set_must_name_what_it_delivers_and_no_ack_waives_it(tmp_path):
    """P12: an L4 naming nothing, on an L3 holding a set with no front runner, was judged on the
    whole set's evidence, and the user's ack then waived what is delivered."""
    st = sl.State(_set_project(tmp_path / "a", None))
    miss = st.missing(st.by_id["l4-a"])
    assert any(m.startswith(sl.UNWAIVABLE) for m in miss), miss
    acked = sl.State(_set_project(tmp_path / "b", None, ack="l4-a L4 2026-09-25 user: ship it\n"))
    ok, _ = acked.verdict(acked.by_id["l4-a"])
    assert not ok, "the ack waives the chain, never what is delivered"


def test_control_an_l4_that_names_its_solution_is_judged_on_it(tmp_path):
    st = sl.State(_set_project(tmp_path, "sol-001"))
    assert not any(m.startswith(sl.UNWAIVABLE) for m in st.missing(st.by_id["l4-a"]))


# P13 ------------------------------------------------------------------------------------------

def test_a_diamond_stamped_complete_without_close_carries_nothing(tmp_path):
    """P13: `completed_at` (diamond-progress: "the true ship timestamp") on an L3 left in the
    active list without `close` kept it carrying code."""
    l3 = {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "decisions": RELEASED,
          "theory_gates_status": dict(tsl.EXPOSE_PASSED), "completed_at": "2026-09-24"}
    ok, why = sl.delivery_state(str(_project(tmp_path / "a", [l3])))
    assert not ok and "completed_at" in why, why
    live = {k: v for k, v in l3.items() if k != "completed_at"}
    assert sl.delivery_state(str(_project(tmp_path / "b", [live])))[0], "control: no stamp"


# P14 ------------------------------------------------------------------------------------------

def test_the_build_refusal_prints_its_remedy_and_runs_nothing(tmp_path):
    """P14: the refusal's heredoc was unquoted, so its backticks ran as commands: the agent saw
    `recorded_at: command not found` and a remedy with the field names blanked."""
    p = _project(tmp_path, [NOT_READY])
    r = _gate(p, _write(p, "app/main.py"))
    assert r.returncode == 2
    assert "command not found" not in r.stderr, r.stderr[:300]
    assert "`recorded_at`, `expires`" in r.stderr and "`covers`" in r.stderr
