"""Shell and file-move paths to the diamonds file, from the 2026-10-01 control audit (DL-1370,
batch 1b: P6-P8). Each gap was reproduced on 0.307.3 before it was fixed; every diamond here
records its decisions directly (founder rule, 2026-10-01).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
sys.path.insert(0, str(PLUGIN / "scripts"))
import scale_locks as sl  # noqa: E402

_spec = importlib.util.spec_from_file_location("bash_state_guard",
                                               PLUGIN / "scripts" / "bash_state_guard.py")
bsg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsg)

ACTIVE = ".claude/diamonds/active.yml"
DEVELOP = [{"decision": d} for d in ("set_target", "start_experiment", "commit_to_build")]
RELEASED = [*DEVELOP, {"decision": "release"}]


def _project(tmp_path: Path, doc: dict) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ACTIVE).write_text(yaml.safe_dump(doc))
    return tmp_path


# P7 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "cp new.yml .claude/diamonds/active.yml  # then run migrate_phase.py",
    "python3 scripts/migrate_phase.py --write; cp new.yml .claude/diamonds/active.yml",
    "cp new.yml .claude/diamonds/active.yml && true derive_closing_path.py",
    "python3 scripts/migrate_phase.py --write > .claude/diamonds/active.yml",
])
def test_naming_mycelium_s_own_writer_does_not_excuse_another_write(tmp_path, cmd):
    """P7: the allowed-writer check was a substring test on the whole command."""
    assert bsg.writes_active(cmd, str(_project(tmp_path, {"active_diamonds": []})))


def test_a_quoted_hash_is_not_a_comment(tmp_path):
    cmd = "printf '# a note\\n' > .claude/diamonds/active.yml"
    assert bsg.writes_active(cmd, str(_project(tmp_path, {"active_diamonds": []})))


@pytest.mark.parametrize("cmd", [
    'python3 "/x/plugins/mycelium/scripts/migrate_phase.py" --project-dir . --write',
    "python3 scripts/derive_closing_path.py --diamond d1 --write .claude/diamonds/active.yml",
])
def test_control_mycelium_s_own_writer_run_alone_is_allowed(tmp_path, cmd):
    assert not bsg.writes_active(cmd, str(_project(tmp_path, {"active_diamonds": []})))


# P8 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("cmd", ["mv .claude/diamonds/active.yml /tmp/x.yml",
                                 "git mv .claude/diamonds/active.yml old.yml"])
def test_moving_the_diamonds_file_away_is_refused_like_removing_it(tmp_path, cmd):
    """P8: `rm` was refused; `mv` passed the pre-check and post globbed only files that exist."""
    assert bsg.writes_active(cmd, str(_project(tmp_path, {"active_diamonds": []})))


def test_control_copying_the_diamonds_file_elsewhere_is_reading_it(tmp_path):
    assert not bsg.writes_active("cp .claude/diamonds/active.yml /tmp/backup.yml",
                                 str(_project(tmp_path, {"active_diamonds": []})))


def test_moving_the_diamonds_file_away_through_mcp_is_refused(tmp_path):
    """P8: MCP `move_file` with the diamonds file as its source left nothing to judge."""
    p = _project(tmp_path, {"active_diamonds": [{"id": "l3-a", "scale": "L3",
                                                 "decisions": RELEASED}]})
    payload = {"tool_name": "mcp__filesystem__move_file",
               "tool_input": {"source": str(p / ACTIVE), "destination": "/tmp/x.yml"}}
    assert sl.new_diamond_violations(str(p), payload)
    other = {"tool_name": "mcp__filesystem__move_file",
             "tool_input": {"source": str(p / "notes.md"), "destination": str(p / "n.md")}}
    assert sl.new_diamond_violations(str(p), other) == [], "control: another file"


# P6 -------------------------------------------------------------------------------------------

def _shell_wrote(tmp_path: Path, before: dict, after: dict) -> list[str]:
    p = _project(tmp_path, after)
    state = p / bsg.STATE_REL
    state.mkdir(parents=True)
    (state / "active.yml.before").write_text(yaml.safe_dump(before))
    return bsg._diamond_problems(p, state, "s1")  # what post reports


def test_a_shell_write_that_launches_an_l5_is_reported(tmp_path):
    """P6: the L5 floor ran only on the edit tools; a shell write moved an L5 into delivery and
    post said nothing about it."""
    before = {"active_diamonds": [{"id": "l5-a", "scale": "L5", "decisions": DEVELOP}]}
    after = {"active_diamonds": [{"id": "l5-a", "scale": "L5", "decisions": RELEASED}]}
    out = _shell_wrote(tmp_path, before, after)
    assert any("L5 human-approval floor" in x for x in out), out


def test_a_shell_write_that_adds_personal_data_exposure_is_reported(tmp_path):
    rec = {"recorded_at": "2026-10-01", "audience": "five testers", "channel": "link",
           "data_class": "personal", "until": "2026-10-20", "consent": "signed"}
    before = {"active_diamonds": [{"id": "l3-a", "scale": "L3", "decisions": RELEASED}]}
    after = {"active_diamonds": [{"id": "l3-a", "scale": "L3", "decisions": RELEASED,
                                  "exposures": [rec]}]}
    out = _shell_wrote(tmp_path, before, after)
    assert any("personal" in x and "person" in x for x in out), out


def test_control_a_shell_write_that_moves_no_l5_and_adds_no_person_data_says_neither(tmp_path):
    l5 = {"id": "l5-a", "scale": "L5", "decisions": RELEASED}
    out = _shell_wrote(tmp_path, {"active_diamonds": [l5]},
                       {"active_diamonds": [{**l5, "confidence": 0.5}]})
    assert not any("floor" in x or "personal" in x for x in out), out
