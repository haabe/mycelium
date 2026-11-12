"""Coverage for check_scale_occupancy: records against cycles, per scale."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_scale_occupancy.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cso", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cso"] = m
    spec.loader.exec_module(m)
    return m


def _project(tmp_path, opps, diamonds, outcomes=("out-a",)):
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    doc = {"desired_outcomes": [{"id": o, "metric": o} for o in outcomes], "opportunities": opps}
    (canvas / "opportunities.yml").write_text(yaml.safe_dump(doc))
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(yaml.safe_dump(diamonds))
    return canvas


def test_records_are_outcomes_and_chosen_targets(tmp_path):
    """v0.302.0 (DL-1367): an L2 opens on an outcome and an L3 on an L2's target. Many
    opportunities under one L2, and many ideas under one L3, are the model, not a backlog."""
    m = _mod()
    canvas = _project(tmp_path, [
        {"id": "opp-1", "solutions": [{"id": "sol-1"}, {"id": "sol-2"}]}, {"id": "opp-2"},
    ], {"active_diamonds": [{"id": "l1", "scale": "L1"},
                            {"id": "l2", "scale": "L2", "target": {"opportunity": "opp-1"}}],
        "completed_diamonds": [{"id": "l2-done", "scale": "L2"}]}, outcomes=("out-a", "out-b"))
    assert m.records(canvas) == {"L2": 2, "L3": 1}
    assert m.cycles(canvas)["L2"] == {"active": 1, "ever": 2}
    out = m.findings(canvas)
    assert len(out) == 1 and out[0].startswith("L3: 1 target(s) chosen and no L3 diamond")


def test_an_old_shape_l2_has_no_target_as_the_lock_reads_it(tmp_path):
    """v0.307.1: 0.307.0 stopped reading an L2 on one opportunity as targeting it, and this report
    kept counting it, so it told the user to open an L3 the lock then refused."""
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"active_diamonds": [{"id": "l2", "scale": "L2", "object_ref": "opp-1"}]})
    assert m.records(canvas)["L3"] == 0
    new = _project(tmp_path / "n", [{"id": "opp-1"}],
                   {"active_diamonds": [{"id": "l2", "scale": "L2", "target": "opp-1"}]})
    assert m.records(new)["L3"] == 1, "control: the recorded target"


def test_a_closed_l2_is_read_from_its_state_or_close_decision_not_its_phase(tmp_path):
    m = _mod()
    closed = {"id": "l2", "scale": "L2", "target": "opp-1", "phase": "deliver",
              "decisions": [{"decision": "close"}]}
    labelled = {"id": "l2", "scale": "L2", "target": "opp-1", "phase": "complete"}
    assert m.records(_project(tmp_path / "a", [{"id": "opp-1"}],
                              {"active_diamonds": [closed]}))["L3"] == 0
    assert m.records(_project(tmp_path / "b", [{"id": "opp-1"}],
                              {"active_diamonds": [labelled]}))["L3"] == 1, \
        "a `phase` label alone closes nothing, as in the locks"


def test_active_zero_but_ever_nonzero_is_the_softer_finding(tmp_path):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"completed_diamonds": [{"id": "l2-done", "scale": "L2"}]})
    assert m.findings(canvas) == ["L2: 1 desired outcome(s), 0 active L2 diamond(s) (1 ever)"]


def test_report_and_cli(tmp_path, monkeypatch, capsys):
    m = _mod()
    canvas = _project(tmp_path, [{"id": "opp-1"}],
                      {"active_diamonds": [{"id": "l2", "scale": "L2", "target": "opp-1"}]})
    monkeypatch.setattr("sys.argv", ["x", "--canvas-dir", str(canvas)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "L2: 1 outcome(s); 1 active diamond(s), 1 ever" in out and "FINDING L3:" in out
    empty = tmp_path / "e" / ".claude" / "canvas"
    empty.mkdir(parents=True)
    assert m.report(empty) == 1


_L1_WITH_TRIGGERS = {"active_diamonds": [
    {"id": "l1-strategy", "scale": "L1", "confidence": 0.4, "triggers": [
        {"when": "a change takes twice as long to deliver as it did in the spring",
         "then": "decide again how the work is split",
         "rule_out": "accrued technical debt"},
        {"when": "a second paying customer asks for the self-hosted form",
         "then": "offer an L2 on the self-hosted outcome"},
        {"when": "  ", "then": "an empty event is not a trigger"},
    ]},
    {"id": "l1-bare", "scale": "L1", "confidence": 0.2},
    {"id": "l1-closed", "scale": "L1", "confidence": 0.5, "decisions": [{"decision": "close"}],
     "triggers": [{"when": "never shown", "then": "x"}]},
    {"id": "l2", "scale": "L2", "confidence": 0.3,
     "triggers": [{"when": "not an L1", "then": "not read"}]},
]}


def test_l1_trigger_sets_are_listed_for_every_live_l1(tmp_path):
    """Founder ruling 2026-11-12 ("Triggers on L1 only"): the reader lists each live L1's
    triggers with what it then does and what to rule out first; a closed L1, another scale's
    key and an empty event are not listed; an L1 with none is named with an empty set."""
    m = _mod()
    canvas = _project(tmp_path, [], _L1_WITH_TRIGGERS)
    sets = dict(m.l1_trigger_sets(canvas))
    assert set(sets) == {"l1-strategy", "l1-bare"}
    assert sets["l1-strategy"] == [
        ("when a change takes twice as long to deliver as it did in the spring -> decide again "
         "how the work is split (rule out first: accrued technical debt)"),
        ("when a second paying customer asks for the self-hosted form -> offer an L2 on the "
         "self-hosted outcome"),
    ]
    assert sets["l1-bare"] == []


def test_report_prints_the_trigger_sets(tmp_path, capsys):
    m = _mod()
    canvas = _project(tmp_path, [], _L1_WITH_TRIGGERS)
    assert m.report(canvas) == 0
    out = capsys.readouterr().out
    assert "L1 l1-strategy trigger set (2); look again if one has happened:" in out
    assert "    - when a second paying customer asks" in out
    assert "L1 l1-bare: no trigger set recorded (`triggers`)" in out
    assert "never shown" not in out and "not an L1" not in out


def test_the_trigger_set_is_declared_in_the_diamond_schema(tmp_path, scripts_path, monkeypatch):
    """Step (a) of the four-step rule: `triggers` validates; a trigger with no `when` does not."""
    sys.path.insert(0, str(scripts_path))
    import validate_canvas as v
    schema_dir = SCRIPT.parent.parent / "schemas" / "canvas"
    monkeypatch.setattr(v, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(v, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    canvas = _project(tmp_path, [], _L1_WITH_TRIGGERS)
    assert v.validate_diamonds(canvas, v.build_registry()) == []
    bad = {"active_diamonds": [{"id": "l1", "scale": "L1", "confidence": 0.1,
                                "triggers": [{"then": "x"}]}]}
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(yaml.safe_dump(bad))
    errors = v.validate_diamonds(canvas, v.build_registry())
    assert len(errors) == 1 and "'when' is a required property" in errors[0]


def test_the_rules_say_why_one_type_and_the_writer_names_the_field():
    """The ruling's doc half: diamond-rules records why there is no container type and what a
    trigger set is; wardley-map step 9 writes `triggers`; diamond-assess reports them."""
    plugin = SCRIPT.parent.parent
    rules = " ".join((plugin / "engine" / "diamond-rules.md").read_text(encoding="utf-8").split())
    assert "**WHY THERE IS NO CONTAINER TYPE.**" in rules
    assert "**ONE DIAMOND TYPE, AND L1 CARRIES A TRIGGER SET" in rules
    assert "we need to design the design rules" in rules
    for part in ("(`when`)", "(`then`)", "(`rule_out`;"):
        assert part in rules, part
    wardley = " ".join((plugin / "skills" / "wardley-map" / "SKILL.md").read_text().split())
    step9 = wardley[wardley.index("### 9. Offer the L1 cycle"):wardley.index("## Output")]
    assert "**Write the L1's trigger set**" in step9 and "`triggers` list" in step9
    assess = (plugin / "skills" / "diamond-assess" / "SKILL.md").read_text(encoding="utf-8")
    assert "each live L1's trigger set as the script lists it" in assess
