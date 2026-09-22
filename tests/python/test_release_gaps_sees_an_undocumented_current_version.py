"""The current version must have a changelog section, or the release is a silent no-op.

WHY THIS EXISTS (2026-09-22). `release_gaps.py --check` asked one question — "does every
DOCUMENTED version have a Release?" — and could not ask the other: "is the current version
documented at all?" Every count in that command reads `documented`, so a version with no
changelog section is invisible to all of them.

MEASURED THE DAY THIS WAS ADDED. v0.242.1 was bumped in `CLAUDE.md` and `plugin.json`,
merged to main with all 22 local gates green and CI green, and shipped **no GitHub
Release**. Auto-release builds its body from the changelog section, found none, did
nothing, and reported success. `release_gaps.py --check` then printed *"OK: every
changelog version >= v0.49.0 has a Release (498 documented)"* — true, and useless, because
v0.242.1 was not among the 498.

**The consumer symptom is what makes it worth a gate rather than a habit.** `claude plugin
update` moved a real install 0.242.0 -> 0.242.1 off main, so a consumer was running a
version whose release notes existed nowhere, while two green checks agreed nothing was
wrong.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "mycelium" / "scripts"))

import release_gaps as rg  # noqa: E402


def test_current_version_is_read_from_claude_md(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("# Mycelium\n\n*Version 1.2.3 -- **A thing** (MINOR). Body.*\n",
                 encoding="utf-8")
    assert rg._current_version(str(f)) == "1.2.3"


def test_a_missing_claude_md_returns_none_rather_than_raising(tmp_path):
    """The check must degrade to "cannot tell", not crash the whole gate — and
    returning None means the branch is skipped rather than firing spuriously."""
    assert rg._current_version(str(tmp_path / "nope.md")) is None


def test_floor_compare_is_numeric_not_lexical():
    """`"0.9.0" > "0.49.0"` as strings. A lexical compare would exempt every version
    below v0.5 and quietly disable the check for a whole era of the changelog."""
    assert rg._ge_floor("0.242.1", "0.49.0") is True
    assert rg._ge_floor("0.9.0", "0.49.0") is False
    assert rg._ge_floor("0.49.0", "0.49.0") is True


def test_check_fails_when_the_current_version_is_undocumented(tmp_path, monkeypatch):
    """THE REGRESSION, end to end: a bump with no changelog section must be caught
    BEFORE it merges, because afterwards the commit is permanent and the release
    workflow has already reported success for doing nothing."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# Changelog\n\n## v0.242.0 - something\n\nbody\n",
                         encoding="utf-8")
    claude = tmp_path / "CLAUDE.md"
    claude.write_text("*Version 0.242.1 -- **Undocumented bump** (PATCH).*\n",
                      encoding="utf-8")

    monkeypatch.setattr(rg, "_current_version", lambda path="CLAUDE.md": "0.242.1")
    monkeypatch.setattr(rg, "_released_from_gh", lambda: {"0.242.0"})

    class Args:
        changelog = str(tmp_path / "changelog.md")
        floor = rg.DEFAULT_FLOOR

    assert rg._cmd_check(Args()) == 1


def test_check_passes_when_the_current_version_is_documented(tmp_path, monkeypatch):
    """THE COMPLEMENT. The new branch must not fire on the normal case, or every
    release would need a waiver and the gate would be removed within a week."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text(
        "# Changelog\n\n## v0.242.1 - documented\n\nbody\n\n## v0.242.0 - also\n\nbody\n",
        encoding="utf-8")

    monkeypatch.setattr(rg, "_current_version", lambda path="CLAUDE.md": "0.242.1")
    monkeypatch.setattr(rg, "_released_from_gh", lambda: {"0.242.0", "0.242.1"})

    path = str(changelog)

    class Args:
        changelog = path
        floor = rg.DEFAULT_FLOOR

    assert rg._cmd_check(Args()) == 0


def test_the_real_repo_documents_its_own_current_version():
    """Run against the shipped tree: this is the assertion that would have blocked
    the v0.242.1 merge."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "plugins" / "mycelium" / "scripts" / "release_gaps.py"),
         "--check"],
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=False,
    )
    assert "has no changelog section" not in result.stdout, result.stdout


def test_an_unreadable_claude_md_exits_2_rather_than_passing(tmp_path, monkeypatch, capsys):
    """THE FAIL-OPEN GUARD, and `check_fail_open.py` blocked this file's first push to
    force it. `_current_version` returning a silent None made the caller skip its branch,
    so the gate passed BECAUSE it could not look — the exact shape this check exists to
    catch, reproduced inside it. Exit 2 (nothing examined), never 0."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# Changelog\n\n## v0.242.0 - something\n\nbody\n",
                         encoding="utf-8")
    monkeypatch.setattr(rg, "_current_version", lambda path="CLAUDE.md": None)
    monkeypatch.setattr(rg, "_released_from_gh", lambda: {"0.242.0"})
    path = str(changelog)

    class Args:
        changelog = path
        floor = rg.DEFAULT_FLOOR

    assert rg._cmd_check(Args()) == 2
    assert "PRECONDITION FAILED" in capsys.readouterr().err


def test_the_reader_says_why_it_returned_none(tmp_path, capsys):
    """A None that explains itself is the difference between a gap a reader can act on
    and one that looks like a pass."""
    assert rg._current_version(str(tmp_path / "absent.md")) is None
    assert "examined NOTHING" in capsys.readouterr().err

    f = tmp_path / "CLAUDE.md"
    f.write_text("# Mycelium\n\nno version line here\n", encoding="utf-8")
    assert rg._current_version(str(f)) is None
    assert "no `*Version X.Y.Z` line" in capsys.readouterr().err
