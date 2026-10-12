"""The pages say what the build gate does not see (v0.322.7).

WHAT WAS WRONG. README.md said "the agent cannot create a brand new source file" and that building
waits "new files and edits alike". The build gate judges a write it can read: the edit tools and
plain shell writes. A command the agent runs that writes the files for it gives the gate nothing
to read. Replayed on 0.322.3 by a blind read's third round and again on 0.322.6: a scaffolder,
`npm init`, `cargo new`, a clone, a download to a file, a script, `patch` and `git apply` each pass
with nothing said, in a project where a plain redirect to a new source file is refused.

WHAT HOLDS NOW. The mechanism that would close it is not built. The README says the limit in the
maintainer's words, and the system card names the commands.

THIS TEST HOLDS THE PAGES AND THE GATE TOGETHER, BOTH WAYS. While the commands pass the gate, the
pages must say so. The day the gate refuses them, this test fails and says to take the sentences
out: a page that still admits a hole that has been closed is as untrue as one that hides it.
"""

from __future__ import annotations

import json
import os
import shutil
import site
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
GATE = PLUGIN / "hooks" / "discovery-gate.sh"
FIXTURE = ROOT / "tests" / "fixtures" / "run10"
README = (ROOT / "README.md").read_text()
CARD = (ROOT / "docs" / "ai-system-card.md").read_text()

README_SAYS = ("That covers the files the agent writes itself. A command it runs that writes them "
               "for it, a scaffolder or a clone, still gets through.")
CARD_SAYS = "does not see files that a command writes"

#: The eight ways found, as the agent would type them. None is run: the gate reads the text.
NOT_SEEN = {
    "a scaffolder": "npx create-next-app@latest web",
    "npm init": "npm init -y",
    "cargo new": "cargo new svc",
    "a clone": "git clone https://example.com/x.git vendor/x",
    "a download to a file": "curl -o app/cadence/web.py https://example.com/web.py",
    "a script that writes": "python3 tools/gen.py",
    "patch": "patch -p1 < change.diff",
    "git apply": "git apply change.diff",
}
SEEN = "echo 'x = 1' > app/cadence/web.py"


@pytest.fixture
def run10(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def _gate(project: Path, command: str) -> int:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(project)}
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase(), "MYCELIUM_TODAY": "2026-09-25"}
    done = subprocess.run(["bash", str(GATE)], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, cwd=project, timeout=120, check=False)
    return done.returncode


def test_control_a_plain_write_of_a_new_source_file_is_refused(run10):
    """The gate is on in this project; without this the rest would prove nothing."""
    assert _gate(run10, SEEN) == 2


@pytest.mark.parametrize("way", sorted(NOT_SEEN))
def test_a_command_that_writes_the_files_itself_passes_the_gate(run10, way):
    """The limit, as it is today. IF THIS FAILS BECAUSE THE GATE NOW REFUSES THE COMMAND, the
    limit is closed for that way: take it out of the system card, and when all eight are closed
    take the sentence out of the README (the maintainer's wording) and retire this test."""
    assert _gate(run10, NOT_SEEN[way]) == 0, (
        f"the build gate now stops {way!r}; the pages still say it gets through")


def test_the_readme_says_the_limit_beside_the_claim():
    """In the paragraph that says what each hook holds, right after the claim it limits."""
    claim = "new files and edits alike. "
    assert claim + README_SAYS in README


def test_the_system_card_names_what_is_not_seen():
    assert CARD_SAYS in CARD
    line = next(ln for ln in CARD.splitlines() if CARD_SAYS in ln)
    for word in ("scaffolder", "`npm init`", "`cargo new`", "`git clone`", "`curl -o`", "script",
                 "`patch`", "`git apply`"):
        assert word in line, f"the system card's entry does not name {word}"
