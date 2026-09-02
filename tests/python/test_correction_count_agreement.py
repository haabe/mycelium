"""Every counter of corrections.md must return the same number.

WHY THIS TEST EXISTS
--------------------
On 2026-08-09 three shipped artifacts counted the same `corrections.md` and
returned 100, 103 and 141. Each pattern was written in isolation, each looked
reasonable in its own file, and no test compared them — so the disagreement was
only visible to someone who happened to run all three on the same day.

The remedy is not a fourth correct regex. It is this file: one fixture that
defines what an entry is, and one test that every counter is held against. A
counter written next year fails here the moment it disagrees, which is the only
mechanism that scales past the people who remember the bug.

WHAT IT COVERS THAT A UNIT TEST DOES NOT
----------------------------------------
The bash hook cannot import the Python library, so their agreement cannot be a
shared symbol. This test executes the REAL `preflight.sh` against the REAL
fixture in a temp project and parses the banner it prints — the same string an
agent reads at SessionStart. A change to the hook's grep that drifts from
`ENTRY_RE` fails here even though nothing imports anything.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins" / "mycelium" / "scripts"
HOOK = REPO / "plugins" / "mycelium" / "hooks" / "preflight.sh"
FIXTURE = REPO / "tests" / "fixtures" / "corrections" / "mixed.md"

#: Stated here AND in the fixture's own header, deliberately. A number that
#: lives only in the test can be "fixed" by editing the test, which is how a
#: fixture stops defining anything. Two statements of it means an edit to either
#: one is visible in review.
EXPECTED = 8

#: The dates the fixture's entries carry, in document order, WITHOUT the
#: disambiguating letter. `2026-01-03b` is a second entry on 2026-01-03, not a
#: date called "2026-01-03b" — a counter that returns the suffix breaks every
#: comparison against a real cutoff, silently, in the direction of "newer".
EXPECTED_DATES = [
    "2026-01-01",
    "2026-01-02",
    "2026-01-03",
    "2026-01-03",
    "2026-01-05",
    "2026-01-06",
    "2026-01-06",
    "2026-01-07",
]

sys.path.insert(0, str(SCRIPTS))
import _corrections_lib  # noqa: E402


def test_fixture_exists_and_is_the_shared_definition():
    """A missing fixture must fail loudly, not skip every agreement check."""
    assert FIXTURE.is_file(), (
        f"{FIXTURE} is the shared definition of a correction entry. "
        "Without it every counter below is untested and silently free to drift."
    )
    header = FIXTURE.read_text(encoding="utf-8")[:1200]
    assert f"EXPECTED ENTRY COUNT: {EXPECTED}" in header, (
        "The fixture's stated count and this test's EXPECTED have diverged. "
        "Whichever one you changed, change the other in the same commit."
    )


def test_library_counts_the_fixture():
    text = FIXTURE.read_text(encoding="utf-8")
    assert _corrections_lib.count(text) == EXPECTED


def test_library_strips_the_disambiguating_suffix_from_dates():
    text = FIXTURE.read_text(encoding="utf-8")
    assert _corrections_lib.entry_dates(text) == EXPECTED_DATES


def test_every_body_is_non_empty_including_the_last():
    """A body sliced to the next mark must still terminate at EOF.

    The last entry is the one that breaks: a slice `text[start:next_start]` with
    no next mark yields "" unless the end is clamped to len(text), and a
    classifier reading "" reports "no signal" rather than failing.
    """
    text = FIXTURE.read_text(encoding="utf-8")
    bodies = [body for _, body in _corrections_lib.entries(text)]
    assert len(bodies) == EXPECTED
    assert all(body.strip() for body in bodies)
    assert "terminates at end-of-file" in bodies[-1]


def test_non_entries_in_the_fixture_are_not_counted():
    """The fixture deliberately contains near-misses; name them explicitly.

    Asserting the total alone would pass if a counter dropped a real entry and
    gained a false one — which is exactly what the preflight banner was doing.
    """
    text = FIXTURE.read_text(encoding="utf-8")
    matched = {m.group(0) for m in _corrections_lib.entry_marks(text)}
    for near_miss in (
        "### Prevention rule",
        "### Not a dated heading at all",
    ):
        assert not any(near_miss in m for m in matched), (
            f"{near_miss!r} is a section heading inside an entry, not an entry. "
            "Counting it is how the banner over-reported and under-reported at once."
        )
    assert not any(m.startswith("- This bullet") for m in matched)
    assert not any("Not an entry either" in m for m in matched)
    # Added 2026-09-02. A bullet may carry a bold title AND a parenthesised date
    # and still be prose: the date must sit inside the first bold span. Without
    # this, a body bullet citing a dated sibling splits its own entry in two and
    # the phantom half classifies as "no catcher" — which is how a compliant
    # entry drew a guard warning and lowered the attribution denominator.
    assert not any("Also not an entry" in m for m in matched), (
        "A parenthesised date in mid-sentence prose is a citation, not an entry "
        "marker. ENTRY_RE must require the date inside the leading `**...**`."
    )


def _run_hook(project_dir: Path) -> str:
    result = subprocess.run(
        ["bash", str(HOOK)],
        # check=False deliberately: a non-zero exit is asserted below with the
        # hook's own stderr attached, which is a far more useful failure than
        # CalledProcessError's traceback.
        check=False,
        capture_output=True,
        text=True,
        env={
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "TMPDIR": str(project_dir / "tmp"),
        },
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.fixture
def project_with_fixture(tmp_path):
    memory = tmp_path / ".claude" / "memory"
    memory.mkdir(parents=True)
    (tmp_path / "tmp").mkdir()
    (memory / "corrections.md").write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return tmp_path


def test_preflight_banner_agrees_with_the_library(project_with_fixture):
    """The bash hook and the Python library must not drift apart.

    This is the cross-language half, and the only one that catches a hook edit.
    """
    out = _run_hook(project_with_fixture)
    match = re.search(r"(\d+) corrections in memory", out)
    assert match, f"banner did not report a count: {out!r}"
    assert int(match.group(1)) == EXPECTED, (
        f"preflight.sh counted {match.group(1)}, the library counts {EXPECTED}. "
        "The ERE in the hook has drifted from ENTRY_RE in _corrections_lib.py."
    )


def test_preflight_still_distinguishes_absent_from_empty(tmp_path):
    """Widening the pattern must not collapse the three honest states.

    "not initialized", "initialized and empty", and "N entries" are different
    facts, and a bare "0 corrections" reads as a counting failure (opp-001).
    """
    (tmp_path / "tmp").mkdir()
    memory = tmp_path / ".claude" / "memory"
    memory.mkdir(parents=True)

    assert "Memory not yet initialized" in _run_hook(tmp_path)

    (memory / "corrections.md").write_text(
        "# Corrections\n\nNothing logged yet.\n", encoding="utf-8"
    )
    assert "Memory is empty" in _run_hook(tmp_path)


def test_cluster_reconcile_reads_the_same_entries(project_with_fixture):
    """The third counter, which was heading-only until 2026-08-09.

    Its bullet blind spot had zero live impact when found — no bullet entry was
    newer than the catalogue cutoff — so a patch would have been unfalsifiable.
    Here the fixture's newest entries include both shapes, so the blind spot is
    the difference between a pass and a fail.
    """
    sys.path.insert(0, str(SCRIPTS))
    import check_cluster_reconcile as ccr

    text = (project_with_fixture / ".claude" / "memory" / "corrections.md").read_text()
    dates, total = ccr.corrections_after(text, cutoff=None)
    assert total == EXPECTED
    assert sorted(EXPECTED_DATES) == dates

    after, total = ccr.corrections_after(text, cutoff="2026-01-04")
    assert total == EXPECTED
    # 2026-01-05, 2026-01-06, 2026-01-06 are bullet-form; 2026-01-07 is a
    # heading. A heading-only counter returns one date here instead of four.
    assert after == ["2026-01-05", "2026-01-06", "2026-01-06", "2026-01-07"]


def test_attribution_reads_the_same_entries(project_with_fixture):
    sys.path.insert(0, str(SCRIPTS))
    import check_correction_attribution as cca

    text = (project_with_fixture / ".claude" / "memory" / "corrections.md").read_text()
    assert len(cca._entries(text)) == EXPECTED


#: The two shapes an entry pattern is anchored on. Narrow on purpose.
#:
#: A first version of this check flagged any `re.compile` containing an ISO date
#: near a script that reads corrections.md, and it fired on
#: `check_cluster_reconcile.py`'s CLUSTER_DATE_RE — a pattern for table rows in
#: `cluster-instances.md`, a different file, doing a different job. That is a
#: false positive of the worst kind for a guard nobody wants to argue with: it
#: teaches people to widen the exclusion list until the guard means nothing.
#:
#: So match the ANCHOR, not the date. Every one of the four historical offenders
#: began with a markdown heading or bold-bullet anchor; no legitimate non-entry
#: pattern in this tree does.
ENTRY_ANCHORS = (r"^#{2,", r"^- \*\*", r"^-[ \t]+\*\*", r"^-[[:space:]]+\*\*")


def test_no_counter_carries_a_private_pattern():
    """The mechanism, not the symptom.

    Three correct regexes today become four regexes and two answers the next
    time someone counts. Any script that counts corrections must reach the
    definition through the shared library rather than restate it.
    """
    offenders = []
    for script in sorted(SCRIPTS.glob("*.py")):
        if script.name == "_corrections_lib.py":
            continue
        source = script.read_text(encoding="utf-8", errors="replace")
        # Only look at real code — the account of the bug quotes old patterns,
        # and a comment explaining what went wrong must not itself be a finding.
        code = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith("#")
        )
        if "corrections.md" not in code:
            continue
        for anchor in ENTRY_ANCHORS:
            if anchor in code:
                offenders.append(f"{script.name}: {anchor!r}")
    assert not offenders, (
        "These scripts read corrections.md and anchor their own entry pattern. "
        "Use _corrections_lib so every counter agrees:\n  " + "\n  ".join(offenders)
    )


def test_the_private_pattern_guard_can_actually_fail(tmp_path):
    """A guard that has never been red has not been tested — it has been run.

    The check above passes trivially if its anchors never match anything. Plant
    the defect it exists to catch and require it to be found.
    """
    planted = tmp_path / "check_invented_counter.py"
    planted.write_text(
        'import re\n'
        'PATH = ".claude/memory/corrections.md"\n'
        'MINE = re.compile(r"^#{2,3}\\\\s+(\\\\d{4}-\\\\d{2}-\\\\d{2})")\n',
        encoding="utf-8",
    )
    code = planted.read_text(encoding="utf-8")
    assert "corrections.md" in code
    assert any(anchor in code for anchor in ENTRY_ANCHORS), (
        "The anchor list no longer matches a hand-rolled entry pattern, so the "
        "guard above cannot fail and is decoration."
    )
