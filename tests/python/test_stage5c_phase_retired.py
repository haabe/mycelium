"""The phase is no longer read (v0.306.0, phase migration stage 5c-1; DL-1368 S4).

A diamond with only a `phase` is in discover, a refusal on it says how to migrate, a release needs
an exposure record, and the migration reads the recorded field, carries a closing phase into
`state`, and is judged against where the diamonds were recorded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))
import migrate_phase as mp
import scale_locks as sl

PURPOSE = {"why": "Swaps are approved in one place so nobody relays them by hand",
           "who": {"description": "Shift leads at cafes with 2-10 sites"}}


def _root(tmp_path: Path, diamonds: list[dict]) -> Path:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True)
    (c / "diamonds").mkdir(parents=True)
    (c / "canvas" / "purpose.yml").write_text(yaml.safe_dump(PURPOSE))
    (c / "canvas" / "opportunities.yml").write_text("opportunities: []\n")
    (c / "diamonds" / "active.yml").write_text(yaml.safe_dump({"active_diamonds": diamonds}))
    return tmp_path


def test_a_diamond_with_only_a_phase_is_in_discover_and_is_told_to_migrate(tmp_path):
    d = {"id": "l3", "scale": "L3", "phase": "develop"}
    assert sl.phase_of(d) == "discover"
    miss = sl.State(str(_root(tmp_path, [d]))).stage_missing(d, "build")
    assert any("records only `phase: develop`" in m and "migrate_phase.py" in m for m in miss)
    assert not any("records only" in m for m in sl.State(str(tmp_path)).stage_missing(
        {"id": "l3", "scale": "L3"}, "build")), "a diamond with no phase is not told to migrate"


def test_a_release_with_no_exposure_record_is_refused(tmp_path):
    d = {"id": "l3", "scale": "L3", "decisions": [{"decision": x} for x in (
        "set_target", "start_experiment", "commit_to_build", "release")]}
    verdict, why = sl._release_decision(str(_root(tmp_path, [d])), "fly deploy")
    assert verdict == "deny" and "No exposure record covers it" in why


def test_a_phase_that_closed_a_diamond_becomes_its_state(tmp_path):
    root = _root(tmp_path, [{"id": "l3", "scale": "L3", "phase": "killed"}])
    assert mp.main(["--project-dir", str(root), "--write"]) == 0
    d = yaml.safe_load((root / ".claude/diamonds/active.yml").read_text())["active_diamonds"][0]
    assert d["state"] == "killed" and not sl.State(str(root)).is_open(d)


def test_the_migration_reads_the_recorded_field_and_moves_nothing(tmp_path, capsys):
    root = _root(tmp_path, [{"id": "l1", "scale": "L1", "phase": "develop"}])
    assert mp.main(["--project-dir", str(root), "--write"]) == 0, capsys.readouterr().out
    d = yaml.safe_load((root / ".claude/diamonds/active.yml").read_text())["active_diamonds"][0]
    assert sl.phase_of(d) == "develop", "converted from the recorded field, not from phase_of"
    assert "REFUSED" not in capsys.readouterr().out
