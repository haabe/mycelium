"""Confidence is a judgement, and a gate status is one of the words the readers know.

WHAT WAS WRONG. `engine/confidence-thresholds.yml#scoring` published four weights and six evidence
values that no file in the plugin read, while diamond-progress step 3 said "Apply scoring rules",
so a reader took 0.4 / 0.3 / 0.2 / 0.1 as the definition of a number two runs on the same record
scored 0.60 and 0.35. And `theory_gates_status` was `{"type": "object"}`: any value validated,
while the gate checks read only a handful of words, so `evidence: done` read as a gate not passed
and nothing said why.

FOUNDER RULING 2026-11-12, "Label it a judgement": the weights are labelled guidance for a
judgement, and the schema gives each gate a status enum.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scale_locks  # noqa: E402
import validate_canvas  # noqa: E402

WEIGHTS = ("evidence_weight", "theory_gate_weight", "validation_weight", "peer_review_weight",
           "evidence_values")


def _errors(tmp_path: Path, monkeypatch, gates_yaml: str) -> list[str]:
    schema_dir = PLUGIN / "schemas" / "canvas"
    monkeypatch.setattr(validate_canvas, "SCHEMA_DIR", schema_dir)
    monkeypatch.setattr(validate_canvas, "COMMON_SCHEMA", schema_dir / "_common.schema.json")
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir()
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(
        "active_diamonds:\n"
        "  - id: l3-x\n"
        "    scale: L3\n"
        "    confidence: 0.3\n"
        "    theory_gates_status:\n" + gates_yaml
    )
    return validate_canvas.validate_diamonds(canvas, validate_canvas.build_registry())


def _documented() -> list[str]:
    """The statuses engine/diamond-rules.md documents, read from its own line."""
    text = (PLUGIN / "engine" / "diamond-rules.md").read_text()
    m = re.search(r"^\s*<gate>: \[([^\]]+)\]", text, re.MULTILINE)
    assert m, "diamond-rules.md no longer documents the gate statuses on a `<gate>: [...]` line"
    return [w.strip() for w in m.group(1).split("|")]


@pytest.mark.parametrize("bad", ["done", "Pass", "insufficient_evidence", "passs"])
def test_the_schema_rejects_a_status_no_reader_knows(tmp_path, monkeypatch, bad):
    """RED ON THE OLD SCHEMA: `theory_gates_status` was a bare object, so every one validated."""
    errors = _errors(tmp_path, monkeypatch, f"      evidence: {bad}\n")
    assert any("theory_gates_status" in e and bad in e for e in errors), errors


def test_the_schema_accepts_every_documented_status(tmp_path, monkeypatch):
    documented = _documented()
    assert set(documented) == {"pass", "pass-with-risk", "fail", "pending", "n/a"}
    gates = "".join(f"      g{i}: {v}\n" for i, v in enumerate(documented))
    assert _errors(tmp_path, monkeypatch, gates) == []


def test_the_schema_accepts_every_word_the_gate_checks_read(tmp_path, monkeypatch):
    """`passed` and `not-applicable` are read by scale_locks as pass and n/a. A schema that
    rejected them would fail a canvas the gates accept."""
    words = sorted(scale_locks.PASSED | scale_locks.NOT_APPLICABLE)
    gates = "".join(f"      g{i}: {v}\n" for i, v in enumerate(words))
    assert _errors(tmp_path, monkeypatch, gates) == []


def test_the_shipped_fixtures_still_validate(tmp_path, monkeypatch):
    """Every theory_gates_status value in the shipped fixtures and the interview's L0 template."""
    found: set[str] = set()
    for path in (ROOT / "tests").rglob("active.yml"):
        found |= set(re.findall(r"^\s{4,}[a-z_]+: (pass-with-risk|pass|pending|fail|n/a)\s*$",
                                path.read_text(), re.MULTILINE))
    found.add("pending")  # skills/interview/SKILL.md initialises every gate to pending
    gates = "".join(f"      g{i}: {v}\n" for i, v in enumerate(sorted(found)))
    assert _errors(tmp_path, monkeypatch, gates) == []


def test_the_weights_are_labelled_a_judgement():
    text = (PLUGIN / "engine" / "confidence-thresholds.yml").read_text()
    assert "GUIDANCE FOR A JUDGEMENT, NOT A FORMULA" in text
    assert "NO CODE\n# COMPUTES CONFIDENCE FROM THEM" in text
    skill = (PLUGIN / "skills" / "diamond-progress" / "SKILL.md").read_text()
    assert "Apply scoring rules from" not in skill
    assert "No\n     code computes confidence from those weights" in skill


def test_the_label_is_true_no_script_or_hook_reads_the_weights():
    """The label says nothing computes confidence from the weights. If a script starts reading
    them, the label is wrong: change it in the same commit, and this test with it."""
    readers = [p.relative_to(PLUGIN).as_posix()
               for d in ("scripts", "hooks") for p in (PLUGIN / d).rglob("*")
               if p.is_file() and p.suffix in (".py", ".sh")
               and any(w in p.read_text(errors="ignore") for w in WEIGHTS)]
    assert readers == []
