"""Coverage for method-aware G-D2 triangulation (v0.91.0).

THE DEFECT. `check_source_independence.py` judged evidence-method diversity by
`source_class`, which is a coarse proxy for method: observed behaviour and an
unprompted articulation are both `external_human`; a controlled experiment, a blind
replication and log forensics are all `external_data`.

Canvases already annotate HOW a source was obtained, inside the `evidence_sources[]`
string — "juniors-dev-presentation [interventional — Frida named four-risks
unprompted]". The check never read it.

THE CONSEQUENCE, 2026-08-05 dogfood: `need-001` carries observed behaviour, an
unprompted articulation and an aggregation — three methods — and reported as
single-coverage because all three are `external_human`. **Acting on that report would
have downgraded correctly-graded evidence.** A check whose remedy damages the canvas
is worse than one that stays quiet.

The fix must be precise in BOTH directions, which is what these tests pin:
  - it must STOP flagging entries the canvas has shown to be multi-method, and
  - it must STILL flag entries that are genuinely single-method, including ones the
    old source_class proxy missed (it caught `need-002`, 4 sources all
    `interventional`, previously invisible).
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_source_independence.py"


def _mod():
    spec = importlib.util.spec_from_file_location("csi", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["csi"] = m
    spec.loader.exec_module(m)
    return m


def _prov(sources):
    return {"evidence_sources": sources}


# ------------------------------------------------------------------ extraction

def test_extracts_human_method_tags():
    methods, aside = _mod()._method_tags(_prov([
        "drew-hoskins-takehome [behavior_validated]",
        "juniors-dev-presentation [interventional — Frida named four-risks unprompted]",
    ]))
    assert methods == {"behavior_validated", "interventional"}
    assert aside == 0


def test_extracts_technical_method_tags():
    methods, _ = _mod()._method_tags(_prov([
        "Five live runs, sandbox-on/off [controlled_experiment]",
        "BLIND SUBAGENT given no access to the diagnosis [blind_replication]",
        "opencode session logs [artifact_forensics]",
    ]))
    assert methods == {"controlled_experiment", "blind_replication", "artifact_forensics"}


@pytest.mark.parametrize("tag", ["anecdotal", "data", "speculation"])
def test_grade_words_are_not_methods(tag):
    """`[anecdotal]` is a ladder position, not a method. Counting it would let a
    grade label masquerade as independent coverage."""
    methods, _ = _mod()._method_tags(_prov([f"some source [{tag}]"]))
    assert methods == set()


@pytest.mark.parametrize("tag", ["aggregated", "consistency_only"])
def test_weak_tags_are_set_aside_not_counted(tag):
    """Neither is independent observation: `aggregated` rolls up sources already
    counted elsewhere, `consistency_only` is correlation the project's own
    Technique 4 exists to downgrade. Letting either supply the second method would
    let a weak source rescue a single-method claim."""
    methods, aside = _mod()._method_tags(_prov([
        "observed [behavior_validated]", f"rolled up [{tag}]",
    ]))
    assert methods == {"behavior_validated"}
    assert aside == 1


# --------------------------------------------------------- both directions

def test_multi_method_entry_is_not_flagged(tmp_path):
    """The need-001 case. Three methods, one source_class — must NOT be flagged."""
    m = _mod()
    methods, _ = m._method_tags(_prov([
        "a [behavior_validated]", "b [behavior_validated]",
        "c [interventional]", "d [aggregated]",
    ]))
    assert len(methods) > 1, "multi-method entry must clear G-D2"


def test_single_method_entry_is_still_flagged(tmp_path):
    """The need-002 case, which the source_class proxy MISSED: four sources, all
    `interventional`. Sources can differ and still share one method's blind spot."""
    methods, _ = _mod()._method_tags(_prov([f"s{i} [interventional]" for i in range(4)]))
    assert len(methods) == 1, "single-method entry must still be flagged"


def test_untagged_sources_fall_back_to_source_class():
    """No tags means the canvas said nothing about method, and the caller must fall
    back rather than treat silence as diversity."""
    methods, aside = _mod()._method_tags(_prov(["CI run 26777731498 — disk paths captured"]))
    assert methods == set() and aside == 0
