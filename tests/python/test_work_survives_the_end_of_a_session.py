"""What a user leaves with must survive the session, and a new session must not deny what it cannot see.

REGRESSION (v0.244.0), from end-to-end dogfood runs on the installed plugin, where a simulated
founder used Mycelium over several sessions with no harness instructions:
  - a call script drafted in one session was asked for in the next, and the new session said
    "I never wrote one"; in another run, "I have no record of your earlier backup question";
  - the founder left /mycelium:start after question 3, and later sessions built on a project with
    no purpose; the purpose check passed only because there was nothing to check against.

Pinned where each decision is made: the always-on operating contract, the interview skill, the
skills that hand the person something to use later (handoff, user-interview, launch-tier), and the
SessionStart hook's helper (the hook itself is covered by tests/bash/test_session_start_unfinished_discovery.sh).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
CONTRACT = PLUGIN / "engine" / "agent-operating-contract.md"
INTERVIEW = PLUGIN / "skills" / "interview" / "SKILL.md"
HELPER = PLUGIN / "scripts" / "_hook_input.py"
SKILLS = PLUGIN / "skills"


def _step(text: str, marker: str) -> str:
    """The numbered step that starts at `marker`, up to the next numbered step or heading."""
    start = text.index(marker)
    rest = text[start + len(marker):]
    nxt = re.search(r"\n(?:\d+[a-z]?\. |#)", rest)
    return text[start:start + len(marker) + (nxt.start() if nxt else len(rest))]


def test_contract_says_take_away_material_goes_in_a_file():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "**written to a file in the project when you produce it**" in text
    assert ".claude/handoffs/" in text


# The founder's ruling of 2026-11-12 ("In the skills"): contract rule 13 was delivered and not
# followed (an E2E run on 0.244.0 drafted SMS messages twice and wrote neither to a file), so the
# skills that hand the person something to use later write it to a file as one of their own
# numbered steps, and say where. No detector. Each pin reads the numbered step, not the whole page,
# so a mention elsewhere (the Output list) cannot stand in for the step.
_TAKE_AWAY_STEPS = (
    ("handoff", "4d. **Write the take-away to a file, and say where (contract rule 13).**"),
    ("user-interview", ("6. **Write the interview guide and every drafted message to a file, "
                        "and say where (contract rule 13).**")),
    ("launch-tier", "1c. **Write the drafted messages to a file, and say where (contract rule 13).**"),
)


def test_each_take_away_skill_writes_the_file_as_a_numbered_step():
    for skill, marker in _TAKE_AWAY_STEPS:
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert marker in text, f"{skill}: no numbered step writes the take-away to a file"
        step = " ".join(_step(text, marker).split())
        assert ".claude/handoffs/<YYYY-MM-DD>-<slug>.md" in step, f"{skill}: the step names no file"
        assert "name that path in the reply" in step, f"{skill}: the step does not say where"


def test_handoff_writes_the_file_before_the_task_entry():
    text = (SKILLS / "handoff" / "SKILL.md").read_text(encoding="utf-8")
    assert text.index("4d. **Write the take-away") < text.index("5. **Write to `.claude/canvas/human-tasks.yml`**")


def test_contract_forbids_denying_unseen_earlier_work():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "cannot see earlier sessions' conversations" in text
    assert "Never state that the work was not done or never existed" in text


def test_interview_saves_answers_as_they_land_and_resumes():
    text = INTERVIEW.read_text(encoding="utf-8")
    assert "**Save each answer as it lands (v0.244.0).**" in text
    assert "resume it, do not restart it" in text
    assert text.index("interview-in-progress.md") < text.index("### Universal Brief Flow"), (
        "the resume check must come in Phase 0, before the flow it resumes"
    )


def _purpose_state(tmp_path: Path, body: str | None) -> int:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    if body is not None:
        (tmp_path / ".claude" / "canvas" / "purpose.yml").write_text(body)
    return subprocess.run([sys.executable, str(HELPER), "--project-dir", str(tmp_path),
                           "--purpose-state"], check=False).returncode


def test_purpose_state_needs_a_statement_not_a_file(tmp_path):
    assert _purpose_state(tmp_path, None) == 1
    assert _purpose_state(tmp_path, 'why: ""\n') == 1
    assert _purpose_state(tmp_path, 'why: "Swaps are approved in one place so nobody relays them"\n') == 0
