"""tests/python/test_gate_table_parity.py — the documented gate table vs the machinery.

WHY THIS EXISTS (v0.240.0). `theory-gates.md` carries a "Quick Reference: Gates per Scale" table
whose stated purpose is `theory_gates_status` initialization — it is what an agent reads when setting
up a diamond. `confidence-thresholds.yml` carries `required_theory_gates`, which is what the gating
machinery actually reads. **Nothing compared them, and they diverged twice:**

  1. The Landscape and Capacity gates were added in v0.217.0 to `confidence-thresholds.yml` at L1 and
     never added to the table, so the table said 7 where the machinery required 9. An agent following
     it produced a diamond missing two required keys, silently, for three months.
  2. The table said `L3 | All gates` and `L4 | All except JTBD`. Both were true at twelve gates and
     became wrong when a thirteenth was defined. **A relative count cannot survive a gate addition.**

Found 2026-09-22 by walking the six scales by hand for an unrelated feasibility test. No check looked,
which is the whole reason this file exists: the divergence is mechanically decidable and was left to
whether someone happened to read both files in the same sitting.

WHAT THIS DOES NOT CHECK: whether either list is *correct*. It asserts only that the prose a human
follows and the YAML a machine follows say the same thing. Both can be wrong together and this passes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "plugins" / "mycelium" / "engine" / "theory-gates.md"
THRESHOLDS = ROOT / "plugins" / "mycelium" / "engine" / "confidence-thresholds.yml"

#: The SECOND machine-followed gate table. `/interview` tells an agent to initialise
#: `theory_gates_status` from this one, so it has the same authority as the engine table
#: and drifted identically — L1 at 7, "All 12 gates" at L3, "All except jtbd" at L4.
#: v0.240.0 fixed the engine table and left this one, which is the fix-one-surface class
#: inside the fix for the fix-one-surface class. Any future per-scale gate list belongs
#: in this tuple; a table nothing compares is a table that drifts.
INTERVIEW = ROOT / "plugins" / "mycelium" / "skills" / "interview" / "SKILL.md"

#: Prose name in the table -> key in required_theory_gates.
ALIASES = {
    "delivery metrics": "delivery_metrics",
    "four risks": "four_risks",
    "service quality": "service_quality",
    "service & usability quality": "service_quality",
    "explainability": "explainability",
}


def _quick_reference() -> str:
    """ONLY the Quick Reference section. Scoping matters: `theory-gates.md` has many
    tables whose rows also start `| L4 |`, and several legitimately contain the word
    "all" (the XAI gate's "All XAI stages applicable to the tier"). A whole-file regex
    matched those and failed on correct prose — an over-broad range, which is the same
    mistake in check form that the table itself suffered in content form."""
    text = TABLE.read_text(encoding="utf-8")
    start = text.index("### Quick Reference: Gates per Scale")
    rest = text[start + 1:]
    end = rest.find("\n### ")
    return rest if end == -1 else rest[:end]


def _table_rows() -> dict[str, tuple[int, set[str]]]:
    text = _quick_reference()
    rows = {}
    for scale, count, names in re.findall(r"^\| (L[0-5]) \| (\d+) \| (.+?) \|$", text, re.MULTILINE):
        cleaned = names.replace("**", "")
        gates = set()
        for raw in cleaned.split(","):
            n = raw.strip().lower()
            gates.add(ALIASES.get(n, n.replace(" ", "_")))
        rows[scale] = (int(count), gates)
    return rows


def _machinery() -> dict[str, set[str]]:
    doc = yaml.safe_load(THRESHOLDS.read_text(encoding="utf-8"))
    return {s: set(v["required_theory_gates"]) for s, v in doc["scales"].items()}


def test_every_scale_appears_in_the_table():
    """A scale the machinery gates but the table omits is unreachable guidance."""
    missing = sorted(set(_machinery()) - set(_table_rows()))
    assert not missing, f"scales in confidence-thresholds.yml with no table row: {missing}"


@pytest.mark.parametrize("scale", sorted(_machinery()))
def test_table_gate_set_matches_machinery(scale):
    """THE LOAD-BEARING ASSERTION. The set, not just the count — a table could carry
    the right number of the wrong gates and a count check would pass it."""
    count, documented = _table_rows()[scale]
    required = _machinery()[scale]
    assert documented == required, (
        f"{scale}: table documents {sorted(documented)}, "
        f"machinery requires {sorted(required)}. "
        f"Missing from table: {sorted(required - documented)}. "
        f"Extra in table: {sorted(documented - required)}."
    )
    assert count == len(required), f"{scale}: table count {count} != {len(required)} gates required"


def test_no_row_uses_a_relative_count():
    """`All gates` and `All except JTBD` were both true once and both went stale the
    moment a gate was added. A relative phrase cannot survive the next addition, so it
    is banned outright rather than corrected each time."""
    text = _quick_reference()
    offenders = [
        line.strip() for line in text.splitlines()
        if re.match(r"^\| L[0-5] \|", line) and re.search(r"\ball\b", line, re.IGNORECASE)
    ]
    assert not offenders, (
        "gate-table rows must name every gate explicitly, never 'all' or 'all except': "
        f"{offenders}"
    )


def test_guard_bites_on_a_divergent_table(tmp_path, monkeypatch):
    """NEGATIVE CONTROL, and it must exercise the REAL parser rather than compare two
    literals. An earlier version of this test asserted `{"a"} != {"a","b"}`, which is
    true of any two different sets and proves nothing about the check above it — the
    assert-nothing-and-report-green shape `_assert.sh` was hardened against in v0.234.1.
    This builds a table that has drifted exactly the way the real one did and asserts
    the real comparison catches it."""
    drifted = tmp_path / "theory-gates.md"
    drifted.write_text(
        "### Quick Reference: Gates per Scale (for `theory_gates_status` initialization)\n\n"
        "| Scale | Total Gates | Gate Names |\n"
        "|---|---|---|\n"
        # L1 with Landscape and Capacity dropped — the exact historical divergence.
        "| L1 | 7 | Evidence, Four Risks, JTBD, Cynefin, Bias, BVSSH, Corrections |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("test_gate_table_parity.TABLE", drifted)

    count, documented = _table_rows()["L1"]
    required = _machinery()["L1"]
    assert documented != required, "the parser must see the drift the real table once had"
    assert count != len(required), "and the count check must see it too"
    assert sorted(required - documented) == ["capacity", "landscape"], (
        "the negative control must reproduce the SPECIFIC historical drift, not any difference"
    )


def _interview_rows() -> dict[str, set[str]]:
    """`/interview`'s own initialisation table, which uses bare keys rather than prose."""
    text = INTERVIEW.read_text(encoding="utf-8")
    start = text.index("| Scale | Gates to Initialize |")
    rest = text[start:]
    end = rest.find("\n\n")
    rows = {}
    for scale, names in re.findall(r"^\| (L[0-5]) \| (.+?) \|$", rest[:end], re.MULTILINE):
        rows[scale] = {n.strip().replace("**", "") for n in names.split(",") if n.strip()}
    return rows


@pytest.mark.parametrize("scale", sorted(_machinery()))
def test_interview_table_matches_machinery(scale):
    """THE SECOND TABLE, and the reason this file now takes a tuple of surfaces.

    An agent initialising from `/interview` must get the same gate set as one
    initialising from `theory-gates.md`. They disagreed until v0.241.0: the engine
    table was corrected and this one was not, so which gates a diamond carried
    depended on which document the agent happened to read."""
    documented = _interview_rows()[scale]
    required = _machinery()[scale]
    assert documented == required, (
        f"{scale}: /interview documents {sorted(documented)}, "
        f"machinery requires {sorted(required)}. "
        f"Missing: {sorted(required - documented)}. Extra: {sorted(documented - required)}."
    )


def test_interview_table_uses_no_relative_count():
    """Same ban, same reason: `All 12 gates` was true once and is now wrong."""
    text = INTERVIEW.read_text(encoding="utf-8")
    start = text.index("| Scale | Gates to Initialize |")
    rest = text[start:]
    end = rest.find("\n\n")
    offenders = [
        line.strip() for line in rest[:end].splitlines()
        if re.match(r"^\| L[0-5] \|", line) and re.search(r"\ball\b", line, re.IGNORECASE)
    ]
    assert not offenders, f"/interview gate rows must name every gate: {offenders}"


def test_the_two_tables_agree_with_each_other():
    """Belt and braces. Both could match the machinery per-scale and still be
    compared here, but a direct table-to-table assertion fails with a clearer
    message when a new gate lands in one and not the other."""
    engine = {s: g for s, (_c, g) in _table_rows().items()}
    interview = _interview_rows()
    for scale in sorted(set(engine) & set(interview)):
        assert engine[scale] == interview[scale], (
            f"{scale}: theory-gates.md and /interview disagree. "
            f"engine-only: {sorted(engine[scale] - interview[scale])}, "
            f"interview-only: {sorted(interview[scale] - engine[scale])}"
        )


def test_every_documented_gate_is_actually_defined():
    """A table naming a gate with no `### N. <Name> Gate` heading sends a reader to
    a definition that does not exist — the phantom-reference class this project audits."""
    text = TABLE.read_text(encoding="utf-8")
    defined = set()
    for name in re.findall(r"^### \d+\.\s+(.+?)\s*$", text, re.MULTILINE):
        n = name.lower().replace(" gate", "").split("(")[0].strip()
        defined.add(ALIASES.get(n, n.replace(" ", "_").replace("/", "_")))
    # `DORA / Delivery Metrics` normalises awkwardly; accept its mapped key.
    defined.add("delivery_metrics")
    defined.add("service_quality")
    for scale, (_count, gates) in _table_rows().items():
        unknown = sorted(g for g in gates if g not in defined)
        assert not unknown, f"{scale} names gates with no definition heading: {unknown}"
