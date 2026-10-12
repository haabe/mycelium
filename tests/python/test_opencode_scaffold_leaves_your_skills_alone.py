"""The opencode scaffold does not overwrite or edit a skill that is not its own (v0.322.3).

WHAT WAS WRONG. `provision-skills.sh` copied Mycelium's skills over `.claude/skills/` with one
`cp -R` and then rewrote plugin paths in EVERY markdown and YAML file under that folder. The
skill folders are not namespaced there, so a person's own skill with the same name as one of
Mycelium's was replaced, and their other skills had text edited in place. The starter
`opencode.json` allowed every skill without asking, theirs included. And `/mycelium:setup` wrote
all of it without asking in a non-interactive run whenever it saw a sign of opencode. Found by all
three readers of the second blind read (2026-10-12).

WHAT HOLDS NOW (maintainer's ruling the same day: "Never overwrite, never unasked"). A folder the
script copies carries a marker file; only a marked folder is ever replaced; a folder without one
is skipped and named; only folders copied in the run have their paths rewritten. The starter
config asks before any skill that is not Mycelium's. Setup writes nothing unasked.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import _scratch_git
import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCAFFOLD = PLUGIN / "integrations" / "opencode"
PROVISION = SCAFFOLD / "provision-skills.sh"
MARK = ".mycelium-vendored"
VAR = "${" + "CLAUDE_PLUGIN_ROOT" + "}"
MINE = f"---\nname: interview\n---\nMy own interview skill. It reads {VAR}/engine/notes.md.\n"
OTHER = f"---\nname: my-own\n---\nNothing of Mycelium's. Mentions {VAR}/skills/x in passing.\n"


def _skill_names() -> list[str]:
    return sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    _scratch_git.init(proj)
    for name, text in (("interview", MINE), ("my-own", OTHER)):
        (proj / ".claude" / "skills" / name).mkdir(parents=True)
        (proj / ".claude" / "skills" / name / "SKILL.md").write_text(text)
    return proj


def _provision(proj: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(PROVISION), str(proj)], capture_output=True, text=True,
                          env=_scratch_git.clean_env(), timeout=180, check=False)


def test_a_skill_of_yours_with_one_of_myceliums_names_is_not_replaced(project):
    """RED BEFORE 0.322.3: the file held Mycelium's interview skill afterwards."""
    done = _provision(project)
    assert done.returncode == 0, done.stderr
    assert (project / ".claude" / "skills" / "interview" / "SKILL.md").read_text() == MINE
    assert "LEFT ALONE" in done.stderr and "    interview" in done.stderr


def test_a_skill_of_yours_that_mycelium_does_not_ship_is_not_edited(project):
    """RED BEFORE 0.322.3: its plugin paths were rewritten in place."""
    _provision(project)
    assert (project / ".claude" / "skills" / "my-own" / "SKILL.md").read_text() == OTHER


def test_the_rest_of_myceliums_skills_arrive_marked_and_rewritten(project):
    _provision(project)
    skills = project / ".claude" / "skills"
    arrived = sorted(p.parent.name for p in skills.glob(f"*/{MARK}"))
    assert arrived == [n for n in _skill_names() if n != "interview"]
    left = [str(f) for f in skills.rglob("*.md")
            if f.parent.name not in {"my-own", "interview"} and VAR + "/" in f.read_text()]
    assert left == [], "a copied skill still points at the plugin root"


def test_a_second_run_refreshes_what_it_copied_and_still_skips_yours(project):
    _provision(project)
    copied = project / ".claude" / "skills" / "setup" / "SKILL.md"
    fresh = copied.read_text()
    copied.write_text("stale\n")
    done = _provision(project)
    assert done.returncode == 0, done.stderr
    assert copied.read_text() == fresh
    assert (project / ".claude" / "skills" / "interview" / "SKILL.md").read_text() == MINE


def test_removing_the_marker_makes_a_copied_skill_yours(project):
    """The way to keep an edited copy, and it is written in the marker file itself."""
    _provision(project)
    folder = project / ".claude" / "skills" / "setup"
    assert "delete this file" in (folder / MARK).read_text()
    (folder / MARK).unlink()
    (folder / "SKILL.md").write_text("my edited copy\n")
    done = _provision(project)
    assert (folder / "SKILL.md").read_text() == "my edited copy\n"
    assert "    setup" in done.stderr


def test_control_a_project_with_no_skills_of_its_own_gets_all_of_them(tmp_path):
    proj = tmp_path / "clean"
    _scratch_git.init(proj)
    done = _provision(proj)
    assert done.returncode == 0, done.stderr
    assert "LEFT ALONE" not in done.stderr
    assert sorted(p.parent.name for p in (proj / ".claude" / "skills").glob(f"*/{MARK}")) \
        == _skill_names()


def test_the_starter_config_asks_before_a_skill_that_is_not_myceliums():
    """RED BEFORE 0.322.3: `"*": "allow"`. opencode reads the object as pattern -> action
    (opencode.ai/docs/skills), so the default asks and each of Mycelium's own names is allowed."""
    rules = json.loads((SCAFFOLD / "opencode.json").read_text())["permission"]["skill"]
    assert rules["*"] == "ask"
    assert next(iter(rules)) == "*", "the default comes first, so a named rule after it wins"
    named = {k: v for k, v in rules.items() if k != "*"}
    assert sorted(named) == _skill_names(), "add or remove the skill in opencode.json too"
    assert set(named.values()) == {"allow"}


def test_setup_writes_no_scaffold_unasked():
    """The instruction the agent follows. RED BEFORE 0.322.3: "provision the scaffold" on a sign."""
    skill = (PLUGIN / "skills" / "setup" / "SKILL.md").read_text()
    auto = skill[skill.index("**Auto-mode default** (no interactive user)"):][:900]
    assert "Write nothing." in auto and "by name" in auto
    assert "in which case provision the scaffold" not in skill
