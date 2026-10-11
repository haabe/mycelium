"""A leaf bakeoff is decided by assumption-test verdicts, never by an ICE gap (0.320.0).

Until 0.320.0 a 20% gap in ICE totals decided two things: whether competing leaves were compared
in parallel, and which one won. No source has the rule, and it contradicted what the framework
says elsewhere (a leaf is archived only on a test verdict). The rule was stated in a protocol, a
skill, three engine files and a threshold, so correcting one place and missing another is the
failure to guard: 0.54.0 removed the ICE advancement gate from two files and the third kept it
for four weeks (engine/adaptive-thresholds.md says so).

These tests read the shipped text. They check the statements an agent acts on (conditions,
triggers, the table an assessment fills in), not the history notes, which quote the old wording
on purpose.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"

#: Every file under plugins/mycelium that may name the retired key, and why it does.
BAKEOFF_DELTA_MAY_BE_NAMED_IN = {
    "engine/adaptive-thresholds.md": "the retired-threshold note",
    "orchestration/leaf-bakeoff.md": "the history note on the trigger",
    "schemas/canvas/thresholds.schema.json": "accepts the key in any shape, marked deprecated",
    "scripts/check_cycle_recording.py": "prints the one retired line",
    "skills/framework-health/SKILL.md": "tells the assessor to report the key as retired",
}


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _without_history_notes(text: str) -> str:
    """Drop the `*(Changed ...)*` and `*(Until ...)*` notes, which quote the old rule."""
    return re.sub(r"\*\((?:Changed|Until) .*?\)\*", "", text, flags=re.DOTALL)


def test_no_winner_selection_condition_reads_a_score():
    rules = _text("orchestration/leaf-bakeoff.md")
    conditions = [ln for ln in rules.splitlines() if ln.startswith("**Condition**:")]
    assert len(conditions) == 5, "the five fan-in rules each state one condition"
    for line in conditions:
        assert "ICE" not in line and "%" not in line and "delta" not in line.lower(), line
        assert "assumption" in line, f"a condition reads the test verdicts: {line}"


def test_a_bakeoff_is_triggered_by_untested_assumptions_not_by_a_gap():
    live = _without_history_notes(_text("orchestration/leaf-bakeoff.md"))
    start = live.index("A bakeoff is warranted when:")
    trigger = live[start:live.index("## Bakeoff Workflow")]
    assert "untested" in trigger
    assert "%" not in trigger, "no score gap decides whether leaves are compared"
    assert "It does not decide whether leaves are compared" in trigger
    assert "it does not pick the winner" in trigger


def test_bakeoff_theater_is_about_missing_untested_assumptions():
    live = _without_history_notes(_text("orchestration/leaf-bakeoff.md"))
    theater = next(ln for ln in live.splitlines() if ln.startswith("**Bakeoff Theater**"))
    assert "ICE" not in theater and "%" not in theater, theater
    assert "only one leaf has an untested riskiest assumption" in theater
    assert "verdicts are already recorded" in theater


def test_the_fan_out_skill_states_the_same_rule():
    skill = _without_history_notes(_text("skills/fan-out/SKILL.md"))
    rules = next(ln for ln in skill.splitlines() if "**winner selection rules**" in ln)
    assert "assumption-test verdicts" in rules
    assert "%" not in rules and "ICE delta" not in rules, rules
    assert "The ICE total only orders which assumption is tested first" in skill
    for doc in ("orchestration/agent-teams.md", "orchestration/fan-out-fan-in.md"):
        text = _text(doc)
        assert "assumption-test verdicts" in text, doc
        assert "close race" not in text.lower(), doc
        assert "Compare solutions using updated scores" not in text, doc


def test_the_thresholds_format_block_carries_no_retired_threshold():
    doc = _text("engine/adaptive-thresholds.md")
    block = doc[doc.index("```yaml") + len("```yaml"):]
    block = block[:block.index("```")]
    table = yaml.safe_load(block)["thresholds"]
    assert sorted(table) == ["confidence_calibration", "evidence_staleness"]
    headings = [ln for ln in doc.splitlines() if ln.startswith("### ") and "Bakeoff" in ln]
    assert headings == ["### Bakeoff ICE Delta (RETIRED in 0.320.0)"]
    assert "The system cannot set the bakeoff delta" not in doc


def test_framework_health_has_no_bakeoff_delta_row_to_fill_in():
    skill = _text("skills/framework-health/SKILL.md")
    rows = [ln for ln in skill.splitlines() if ln.startswith("| Bakeoff delta")]
    assert rows == [], "an assessment is not asked to calibrate a retired threshold"
    assert "| Confidence factor | 1.0 |" in skill, "control: the live row is still there"


def test_nothing_calibrates_from_the_retired_threshold():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_ccr_bakeoff", ROOT / "scripts" / "check_cycle_recording.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert "bakeoff_delta" not in module._CALIBRATION_INPUT
    assert "bakeoff_delta" in module._RETIRED_THRESHOLDS
    assert not set(module._CALIBRATION_INPUT) & set(module._RETIRED_THRESHOLDS), (
        "a threshold is live or retired, never both")


def test_the_retired_key_is_named_only_where_it_is_explained():
    """No reader left behind: a new file that names `bakeoff_delta` fails here until someone
    decides whether it reads the key (it must not) or explains it (then list it above)."""
    named_in = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".sh", ".yml", ".yaml", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "bakeoff_delta" in text:
            named_in.add(path.relative_to(ROOT).as_posix())
    assert named_in == set(BAKEOFF_DELTA_MAY_BE_NAMED_IN), (
        sorted(named_in ^ set(BAKEOFF_DELTA_MAY_BE_NAMED_IN)))
