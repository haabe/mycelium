"""The decision log beside the phase, and the migration to it (v0.303.0, stage 5a; DL-1368).

Where a diamond is, is read from its decisions; the recorded phase only when it has none. Adding
decisions is judged as the move they make. migrate_phase.py rewrites the phase history as dated,
reconstructed decisions, a learning delivery as a reconstructed exposure record, and the old L2/L3
shape as the new fields, and refuses to write anything the scale locks read as a change.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import diamond_rulings as dr  # noqa: E402
import migrate_phase as mp  # noqa: E402
import scale_locks as sl  # noqa: E402


def _dec(*names):
    return [{"decision": n, "on": "2026-10-01"} for n in names]


def test_where_a_diamond_is_is_read_from_its_decisions():
    l3 = {"id": "l3", "scale": "L3", "phase": "discover"}
    assert sl.phase_of({**l3, "decisions": _dec("set_target")}) == "define"
    assert sl.phase_of({**l3, "decisions": _dec("set_target", "start_experiment")}) == "define", \
        "develop needs the build commitment too"
    both = _dec("set_target", "start_experiment", "commit_to_build")
    assert sl.phase_of({**l3, "decisions": both}) == "develop"
    assert sl.phase_of({**l3, "decisions": [*both, *_dec("release", "close")]}) == "complete"
    assert sl.phase_of({**l3, "phase": "deliver"}) == "deliver", "no log: the recorded phase"
    assert sl.phase_of({"scale": "L0", "decisions": _dec("state_purpose")}) == "deliver"


def test_a_decision_is_judged_as_the_move_it_makes(tmp_path):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    before = {"id": "l0", "scale": "L0", "phase": "discover"}
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        yaml.safe_dump({"active_diamonds": [before]}))
    bare = {**before, "decisions": _dec("state_purpose")}
    out = sl.violations_between(str(tmp_path), yaml.safe_dump({"active_diamonds": [before]}),
                                yaml.safe_dump({"active_diamonds": [bare]}))
    assert any("cannot move to deliver" in x and "evidence" in x for x in out), out
    passed = {**bare, "theory_gates_status": dict.fromkeys(
        ("evidence", "cynefin", "bias", "bvssh", "corrections"), "pass")}
    out = sl.violations_between(str(tmp_path), yaml.safe_dump({"active_diamonds": [before]}),
                                yaml.safe_dump({"active_diamonds": [passed]}))
    assert out == [], "gates passed: the decision is its own record, no history entry needed"


def test_the_ruling_signature_reads_the_log():
    d = {"scale": "L3", "phase": "discover",
         "decisions": _dec("set_target", "start_experiment", "commit_to_build")}
    assert dr.signature(d).split("|") == ["develop", "", "0", "3"]


PROJECT = {
    "desired_outcomes": [{"id": "out-a", "metric": "a", "north_star_input_ref": "x"}],
    "opportunities": [{"id": "opp-1", "status": "open", "rolls_up_to": "out-a",
                       "solutions": [{"id": "sol-1"}, {"id": "sol-2"}]}],
}
DIAMONDS = {"active_diamonds": [
    {"id": "l0", "scale": "L0", "phase": "deliver",
     "progression_history": [{"transition": "discover -> define", "date": "2026-05-01"}]},
    {"id": "l2", "scale": "L2", "phase": "define", "object_ref": "opp-1"},
    {"id": "l3", "scale": "L3", "phase": "develop", "object_ref": "sol-1", "parent": "l2",
     "progression_history": [{"transition": "define -> develop", "date": "2026-09-20",
                              "ruling": "progressed"}],
     "learning_delivery": {"audience": "two shift leads", "until": "2026-11-01",
                           "means": "by hand", "started": "2026-09-22"}}],
    "completed_diamonds": [{"id": "l4-old", "scale": "L4"}]}


def _project(tmp_path: Path, diamonds=DIAMONDS) -> Path:
    c = tmp_path / ".claude"
    (c / "canvas").mkdir(parents=True)
    (c / "diamonds").mkdir(parents=True)
    (c / "canvas" / "opportunities.yml").write_text(yaml.safe_dump(PROJECT))
    (c / "diamonds" / "active.yml").write_text("# leading note kept\n" + yaml.safe_dump(diamonds))
    return tmp_path


def _load(root: Path) -> dict:
    return yaml.safe_load((root / ".claude" / "diamonds" / "active.yml").read_text())


def test_a_dry_run_writes_nothing(tmp_path, capsys):
    root = _project(tmp_path)
    text = (root / ".claude" / "diamonds" / "active.yml").read_text()
    assert mp.main(["--project-dir", str(root)]) == 0
    assert "Dry run" in capsys.readouterr().out
    assert (root / ".claude" / "diamonds" / "active.yml").read_text() == text


def test_the_migration_keeps_every_diamond_where_it_is(tmp_path, capsys):
    root = _project(tmp_path)
    before = {d["id"]: sl.phase_of(d) for k in ("active_diamonds",) for d in DIAMONDS[k]}
    assert mp.main(["--project-dir", str(root), "--write", "--today", "2026-10-01"]) == 0
    doc = _load(root)
    after = {d["id"]: sl.phase_of(d) for d in doc["active_diamonds"]}
    assert after == before
    assert (root / ".claude" / "diamonds" / "active.yml").read_text().startswith(
        "# leading note kept\n")
    l0, l2, l3 = doc["active_diamonds"]
    assert l0["decisions"] == [{"decision": "state_purpose", "on": "2026-05-01", "ruling": None,
                                "reconstructed": True}]
    dated = [x["on"] for x in l3["decisions"] if x["decision"] == "commit_to_build"]
    assert dated == ["2026-09-20"], "dated from its history entry"
    assert l2["object_ref"] == "out-a" and l2["target"]["opportunity"] == "opp-1"
    assert l3["object_ref"] == "opp-1" and l3["front_runner"] == "sol-1"
    assert "learning_delivery" not in l3
    rec = l3["exposures"][0]
    assert rec["reconstructed"] and rec["audience"] == "two shift leads"
    assert "data_class" not in rec and "consent" not in rec, "never recorded, so not invented"
    capsys.readouterr()
    assert mp.main(["--project-dir", str(root), "--write"]) == 0
    assert "nothing to migrate" in capsys.readouterr().out, "a second run changes nothing"


def test_a_reconstructed_exposure_does_not_cover_a_release(tmp_path):
    root = _project(tmp_path)
    mp.main(["--project-dir", str(root), "--write", "--today", "2026-10-01"])
    _, current, reasons = sl.current_exposures(sl.State(str(root)))
    assert current == []
    assert any("data_class" in r and "consent" in r for r in reasons), reasons


def test_comments_below_the_first_key_are_not_lost_silently(tmp_path, capsys):
    root = _project(tmp_path)
    p = root / ".claude" / "diamonds" / "active.yml"
    p.write_text(p.read_text().replace("completed_diamonds:", "# a note mid-file\ncompleted_diamonds:"))
    assert mp.main(["--project-dir", str(root), "--write"]) == 1
    assert "comment line" in capsys.readouterr().out
    assert "# a note mid-file" in p.read_text(), "refused, nothing written"


def test_the_next_item_offers_the_migration_until_it_has_run(tmp_path):
    import next_item as ni  # only this test needs the picker
    root = _project(tmp_path)
    item = ni._migrate_item(root, "2026-10-01", {})
    assert item and item["id"] == "migrate-phase:project" and ni.agent_owned(item)
    assert "migrate_phase.py" in item["command"] and "--project-dir" in item["command"]
    mp.main(["--project-dir", str(root), "--write", "--today", "2026-10-01"])
    assert ni._migrate_item(root, "2026-10-01", {}) is None, "migrated: nothing to offer"


def test_an_unreadable_file_offers_nothing_and_the_picker_says_why(tmp_path):
    import next_item as ni  # the fail-open review of _migrate_item cites this test
    root = _project(tmp_path)
    (root / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: [broken")
    assert ni._migrate_item(root, "2026-10-01", {}) is None
    _, note = ni.pick(root, "", "2026-10-01")
    assert "unreadable" in note, "reported once, where the human reads it"
