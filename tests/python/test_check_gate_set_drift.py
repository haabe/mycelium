"""tests/python/test_check_gate_set_drift.py — the gate-set copy scanner.

WHY A SCANNER NEEDS DIFFERENT TESTS FROM A COMPARATOR. `test_gate_table_parity.py` asserts that
two KNOWN tables agree. This scanner's job is to find tables nobody listed, so its tests are
about discovery and classification rather than equality:

  - does it find an enumeration in a file not on any list (the undeclared case, which is how
    every drift so far began)
  - does it leave an "etc." list alone (a partial list is allowed to be partial; flagging it
    would train the reader to ignore the check)
  - does it catch a stale `all N gates` count, which drifts without any name changing
  - can it fail at all

THE SELF-EXEMPTION TRAP IS PINNED HERE ON PURPOSE. The scanner matched its own docstring twice
while being written. Both times the fix was to reword the prose, never to skip the file — a
check that excludes itself has a hole shaped exactly like the checker, and this suite asserts
the scanner still scans its own directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"))

import check_gate_set_drift as mod

REAL_ROOT = Path(__file__).resolve().parents[2]

THRESHOLDS = """\
scales:
  L0:
    name: Purpose
    required_theory_gates: [evidence, cynefin, bias, bvssh, corrections]
  L1:
    name: Strategy
    required_theory_gates: [evidence, four_risks, jtbd, cynefin, bias, bvssh, corrections,
                            landscape, capacity]
"""


def _fixture(tmp_path: Path, files: dict[str, str]) -> Path:
    plugin = tmp_path / "plugins" / "mycelium"
    (plugin / "engine").mkdir(parents=True)
    (plugin / "engine" / "confidence-thresholds.yml").write_text(THRESHOLDS, encoding="utf-8")
    for rel, content in files.items():
        path = plugin / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_bites_on_a_drifted_scale_row(tmp_path, capsys):
    """NEGATIVE CONTROL. L1 missing landscape and capacity is the exact historical drift."""
    root = _fixture(tmp_path, {
        "engine/theory-gates.md":
            "| L1 | 7 | evidence, four_risks, jtbd, cynefin, bias, bvssh, corrections |\n",
    })
    assert mod.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "landscape" in out and "capacity" in out, "must name the gates that are missing"


def test_accepts_a_matching_scale_row(tmp_path):
    root = _fixture(tmp_path, {
        "engine/theory-gates.md":
            "| L1 | 9 | evidence, four_risks, jtbd, cynefin, bias, bvssh, corrections, "
            "landscape, capacity |\n",
    })
    assert mod.main(["--root", str(root)]) == 0


def test_leaves_an_illustrative_list_alone(tmp_path, capsys):
    """`feedback-loops.md` names seven gates and ends 'etc.'. It does not claim to be the
    whole set, so comparing it would be a false positive — and a check that fires on correct
    prose is one a reader learns to skip."""
    root = _fixture(tmp_path, {
        "engine/feedback-loops.md":
            "| Per-phase-transition | Theory gates (evidence, four risks, jtbd, cynefin, "
            "bias, security, privacy, bvssh, etc.) |\n",
    })
    assert mod.main(["--root", str(root)]) == 0
    assert "ILLUSTRATIVE" in capsys.readouterr().out


def test_catches_a_stale_count_claim(tmp_path, capsys):
    """`all 12 gates` drifts without any gate name changing — the seventh instance found
    was this exact shape, in a file whose table had just been corrected."""
    root = _fixture(tmp_path, {
        "engine/theory-gates.md": "**Applicable gates**: All 12 gates\n",
    })
    assert mod.main(["--root", str(root)]) == 1
    assert "STALE COUNT CLAIM" in capsys.readouterr().out


def test_reports_an_undeclared_copy(tmp_path, capsys):
    """THE DISCOVERY ASSERTION, and the reason this scanner exists. A file enumerating
    gates that nobody declared is how every drift so far began."""
    root = _fixture(tmp_path, {
        "skills/somewhere-new/SKILL.md":
            "Gates: evidence, four_risks, jtbd, cynefin, bias, bvssh\n",
    })
    assert mod.main(["--root", str(root)]) == 1
    out = capsys.readouterr().out
    assert "UNDECLARED COPY" in out
    assert "somewhere-new" in out


def test_source_of_truth_is_not_compared_to_itself(tmp_path):
    """confidence-thresholds.yml enumerates every gate by definition; scanning it would
    report the source of truth as a drifted copy of itself."""
    root = _fixture(tmp_path, {})
    assert mod.main(["--root", str(root)]) == 0


def test_absent_tree_exits_2_rather_than_reporting_success(tmp_path, capsys):
    """An earlier draft returned 0 here with a message saying "not a pass". The project's
    own `test_check_empty_input_honesty` caught it: only the EXIT CODE is read by CI, the
    pre-push hook and anything chaining on this, so a green on an empty tree is
    indistinguishable from a working check and stays green forever."""
    assert mod.main(["--root", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "PRECONDITION FAILED" in err
    assert "NOTHING WAS SCANNED" in err, "must name what was not verified, not just fail"


def test_the_scanner_scans_its_own_directory(tmp_path):
    """SELF-EXEMPTION GUARD. The scanner matched its own docstring twice while being
    written, and both times the fix was to reword the prose rather than skip the file.
    If someone later adds `scripts/` to an ignore list, this fails."""
    root = _fixture(tmp_path, {
        "scripts/some_check.py":
            '"""Mentions evidence, four_risks, jtbd, cynefin, bias, bvssh in prose."""\n',
    })
    assert mod.main(["--root", str(root)]) == 1, (
        "a .py file under scripts/ that enumerates gates must still be reported; "
        "exempting the scanner's own directory would leave a hole shaped like the scanner"
    )


def test_real_repository_is_clean():
    """The shipped tree must satisfy its own scanner. This is the assertion that would
    have caught all seven historical drifts on the day each landed."""
    assert mod.main(["--root", str(REAL_ROOT)]) == 0


@pytest.mark.parametrize(("prose", "expected"), [
    ("Four Risks", "four_risks"),
    ("Service Quality", "service_quality"),
    ("DORA / Delivery Metrics", "delivery_metrics"),
    ("BVSSH", "bvssh"),
])
def test_prose_spellings_normalise_to_keys(prose, expected):
    """Real tables write gates in prose. A scanner that only matched key form would miss
    every markdown table — which is where all seven drifts actually lived."""
    assert mod._normalise(prose) == expected
