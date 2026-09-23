"""What a user leaves with must survive the session, and a new session must not deny what it cannot see.

REGRESSION (v0.244.0), from end-to-end dogfood runs on the installed plugin, where a simulated
founder used Mycelium over several sessions with no harness instructions:
  - a call script drafted in one session was asked for in the next, and the new session said
    "I never wrote one"; in another run, "I have no record of your earlier backup question";
  - the founder left /mycelium:start after question 3, and later sessions built on a project with
    no purpose; the purpose check passed only because there was nothing to check against.

Pinned where each decision is made: the always-on operating contract, the interview skill, and the
SessionStart hook's helper (the hook itself is covered by tests/bash/test_session_start_unfinished_discovery.sh).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
CONTRACT = PLUGIN / "engine" / "agent-operating-contract.md"
INTERVIEW = PLUGIN / "skills" / "interview" / "SKILL.md"
HELPER = PLUGIN / "scripts" / "_hook_input.py"


def test_contract_says_take_away_material_goes_in_a_file():
    text = CONTRACT.read_text(encoding="utf-8")
    assert "**written to a file in the project when you produce it**" in text
    assert ".claude/handoffs/" in text


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
