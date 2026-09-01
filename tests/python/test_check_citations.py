"""Coverage for check_citations.py — the do-not-cite register scan.

WHY IT EXISTS. On 2026-09-01 an auto-memory do-not-cite register failed twice in one session, in
both directions: a ruled-on citation was written into two canvas files without the register being
read, and hours later a NARROW entry was paraphrased into a broad one and acted on, rewriting four
surfaces that were already correct. The rule existed, was right, and was not consulted at the
moment of use.

THE DESIGN CONSTRAINT THAT MATTERS. This must not become another lexical guard. Its sibling
`absence_claim_guard.py` matches a prose signature and was consumer-measured at 29 lifetime fires,
16 in one day, zero of that day's four confirmed errors caught. This check matches a CURATED list,
so its precision is the register's precision — it cannot fire on a claim nobody ruled on.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_citations.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_cc", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_cc"] = m
    spec.loader.exec_module(m)
    return m


REGISTER = """schema_version: 1
entries:
  - id: bogus-stat
    match: ["42% of teams"]
    verdict: do-not-cite
    verbatim: >-
      No primary source; terminal reference is a vendor blog.
"""


def _project(tmp_path, canvas_text, register=REGISTER):
    (tmp_path / ".claude" / "harness").mkdir(parents=True)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    if register is not None:
        (tmp_path / ".claude/harness/do-not-cite.yml").write_text(register)
    (tmp_path / ".claude/canvas/landscape.yml").write_text(canvas_text)
    return tmp_path


def test_an_unannotated_ruled_on_claim_is_reported(tmp_path):
    p = _project(tmp_path, "notes: |\n  Research shows 42% of teams ship faster.\n")
    findings, scanned, entries = _mod().scan(p)
    assert entries == 1 and scanned == 1
    assert len(findings) == 1
    assert findings[0][3] == "42% of teams"


def test_the_same_claim_inside_a_correction_is_not_reported(tmp_path):
    """The occurrence in a correction is the record of the rule being APPLIED, not broken."""
    p = _project(tmp_path, "notes: |\n  CORRECTED 2026-09-01: 42% of teams has no primary.\n")
    findings, _, _ = _mod().scan(p)
    assert findings == []


def test_annotation_is_detected_at_block_level_not_line_level(tmp_path):
    """MEASURED 2026-09-01: line-level matching gave 3 false positives out of 6 findings, every one
    inside a correction block whose marker sat 1-5 lines above. YAML folds prose across lines, so
    the unit is the block. The false positives named the missing convention."""
    canvas = ("notes: >-\n"
              "  MISATTRIBUTION CORRECTED 2026-09-01. The figure is real but the\n"
              "  institutions are wrong, and the claim that 42% of teams ship faster\n"
              "  traces only to a vendor blog.\n")
    findings, _, _ = _mod().scan(_project(tmp_path, canvas))
    assert findings == [], f"marker was 2 lines up and should have suppressed: {findings}"


def test_a_blank_line_ends_the_block_so_suppression_does_not_leak(tmp_path):
    """An annotation must not silence an unrelated claim further down the file."""
    canvas = ("a: >-\n  CORRECTED 2026-09-01: something unrelated.\n"
              "\n"
              "b: >-\n  Research shows 42% of teams ship faster.\n")
    findings, _, _ = _mod().scan(_project(tmp_path, canvas))
    assert len(findings) == 1, "suppression leaked past a blank line"


def test_an_absent_register_refuses_rather_than_passing(tmp_path):
    """Empty input must refuse. A clean result over nothing is the false green this repo removes."""
    p = _project(tmp_path, "notes: 42% of teams\n", register=None)
    findings, _, entries = _mod().scan(p)
    assert entries == 0 and findings == []


def test_an_empty_entries_list_also_refuses(tmp_path):
    p = _project(tmp_path, "notes: 42% of teams\n", register="schema_version: 1\nentries: []\n")
    findings, _, entries = _mod().scan(p)
    assert entries == 0 and findings == []


def test_a_malformed_register_does_not_raise(tmp_path):
    """It must not crash — reporting is handled by the test below."""
    p = _project(tmp_path, "notes: 42% of teams\n", register="entries: [unclosed\n")
    _mod().scan(p)


def test_it_reports_findings_without_gating(tmp_path):
    """Findings do not fail the run — a citation that looks wrong is sometimes right, which is
    exactly what the second failure of 2026-09-01 established."""
    p = _project(tmp_path, "notes: |\n  Research shows 42% of teams ship faster.\n")
    sys.argv = ["check_citations.py", "--project-dir", str(p)]
    assert _mod().main() == 0


def test_it_refuses_over_an_absent_register(tmp_path):
    """Empty-input honesty: exit 1, not a green pass over nothing.

    This is ALSO why it is not in the blocking pre-push gate set — that hook treats any non-zero
    as failure, so gating on it would block every push from a project that never wrote a register.
    Its automatic reader is validate_canvas, which reports it as a WARN and never fails.
    """
    p = _project(tmp_path, "notes: 42% of teams\n", register=None)
    sys.argv = ["check_citations.py", "--project-dir", str(p)]
    assert _mod().main() == 1


def test_the_dogfood_canvas_is_clean(scripts_path):
    """Zero unannotated occurrences after the three real findings this check surfaced were fixed."""
    live = Path("/Users/bartnes/Repos/mycelium-roadmap")
    if not (live / ".claude/harness/do-not-cite.yml").is_file():
        pytest.skip("dogfood register not present in this checkout")
    findings, _, entries = _mod().scan(live)
    assert entries > 0
    assert findings == [], findings


def test_a_malformed_register_is_reported_not_silently_treated_as_absent(tmp_path):
    """A typo must not silently disable every rule while the check reads green.

    This was a NEW fail-open site flagged by check_fail_open on first run: the original handler
    returned the same "no register" value for a parse error as for a missing file. Absent is a
    not-configured state; malformed is someone believing rules are live when none are.
    """
    p = _project(tmp_path, "notes: 42% of teams\n", register="entries: [unclosed\n")
    findings, _, entries = _mod().scan(p)
    assert entries == -1, "malformed must be distinguishable from absent"
    assert "unreadable" in findings[0][2]["verbatim"]
    sys.argv = ["check_citations.py", "--project-dir", str(p)]
    assert _mod().main() == 1


def test_a_line_that_already_caveats_the_claim_is_not_flagged(tmp_path):
    """MEASURED 2026-09-01: the first extension of the register produced a 6-of-6 FALSE POSITIVE
    run, and one cause was an annotation vocabulary too narrow. A live canvas line read
    "Standish CHAOS cause-ranking (... DISPUTED — use ranking only) [anecdotal/contested]" and was
    reported anyway. Flagging a line that already discloses its own weakness teaches authors that
    disclosure is punished, which is the opposite of the behaviour wanted.
    """
    reg = ('schema_version: 1\nentries:\n  - id: x\n    match: ["42% of teams"]\n'
           '    verdict: do-not-cite\n    verbatim: no primary\n')
    for caveat in ("DISPUTED", "contested", "unverified", "unsourced", "not established"):
        p = _project(tmp_path / caveat,
                     f"notes: |\n  {caveat}: 42% of teams ship faster.\n", register=reg)
        assert _mod().scan(p)[0] == [], caveat


def test_detection_survives_the_widened_suppression(tmp_path):
    """The risk of widening the annotation vocabulary is going blind. An UNcaveated claim must
    still be reported."""
    reg = ('schema_version: 1\nentries:\n  - id: x\n    match: ["42% of teams"]\n'
           '    verdict: do-not-cite\n    verbatim: no primary\n')
    p = _project(tmp_path, "notes: |\n  Research shows 42% of teams ship faster.\n", register=reg)
    assert len(_mod().scan(p)[0]) == 1
