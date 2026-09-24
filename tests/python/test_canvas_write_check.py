"""A canvas write is checked against its schema as it lands (v0.250.0).

E2E run 19 (plugin 0.249.0) wrote `privacy-assessment.yml` with a root `reassessment:` block the schema
rejects. The post-write nudge had already said "validate with validate_canvas.py"; the invalid file
stood until the harness ran the validator. Two causes, pinned here where each lives:
  - nothing ran the schema on the written file and named the error to the agent;
  - /privacy-check asks "Who accesses it?" and "Where is it stored?" and the schema had no field
    for the answer, so a reassessment that found a new sub-processor had nowhere to go.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOK = PLUGIN / "hooks" / "canvas-schema-check.sh"


def _run(project: Path, rel: str, session: str = "s1") -> str:
    payload = json.dumps({"session_id": session,
                          "tool_input": {"file_path": str(project / ".claude" / rel)}})
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN), "CLAUDE_PROJECT_DIR": str(project)}
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                       env=env, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _write(project: Path, rel: str, text: str) -> None:
    p = project / ".claude" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


PRIVACY_OK = """\
last_assessed: "2026-10-12"
data_inventory:
  - data_type: "Approver mobile number"
    retention_period: "while the person approves swaps"
processors:
  - name: "SMS provider"
    role: processor
    data_types: ["Approver mobile number", "message body"]
    location: "EEA data centres"
    retention_period: "60 days"
    agreement: "DPA signed 2026-10-12"
"""


def test_an_unknown_root_key_is_named_to_the_agent(tmp_path):
    _write(tmp_path, "canvas/privacy-assessment.yml",
           'last_assessed: "2026-10-12"\nreassessment:\n  date: "2026-10-12"\n')
    out = json.loads(_run(tmp_path, "canvas/privacy-assessment.yml"))
    assert out["decision"] == "block"
    assert "'reassessment' was unexpected" in out["reason"]


def test_a_valid_canvas_file_says_nothing(tmp_path):
    _write(tmp_path, "canvas/privacy-assessment.yml", PRIVACY_OK)
    assert _run(tmp_path, "canvas/privacy-assessment.yml") == ""


def test_the_privacy_schema_has_a_home_for_processors(tmp_path):
    """The reassessment that found the SMS provider now fits the schema."""
    _write(tmp_path, "canvas/privacy-assessment.yml",
           PRIVACY_OK + "  - name: x\n    role: landlord\n")
    out = json.loads(_run(tmp_path, "canvas/privacy-assessment.yml"))
    assert "landlord" in out["reason"]  # the enum is checked, so the field is really schema'd


def test_broken_yaml_is_named(tmp_path):
    _write(tmp_path, "canvas/privacy-assessment.yml", "last_assessed: [unclosed\n")
    out = json.loads(_run(tmp_path, "canvas/privacy-assessment.yml"))
    assert "YAML parse error" in out["reason"]


def test_the_diamonds_file_is_checked_too(tmp_path):
    _write(tmp_path, "diamonds/active.yml",
           "active_diamonds:\n  - id: d1\n    scale: L9\n    phase: discover\n")
    out = json.loads(_run(tmp_path, "diamonds/active.yml"))
    assert out["decision"] == "block" and "active.yml" in out["reason"]


def test_files_outside_canvas_and_diamonds_are_ignored(tmp_path):
    _write(tmp_path, "state/x.yml", "anything: [unclosed\n")
    assert _run(tmp_path, "state/x.yml") == ""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.yml").write_text("x: [unclosed\n")
    payload = json.dumps({"tool_input": {"file_path": str(tmp_path / "app" / "a.yml")}})
    r = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True, text=True,
                       env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}, timeout=60, check=False)
    assert r.stdout.strip() == ""


def test_the_hook_is_registered_on_every_runtime():
    for name in ("hooks.json", "hooks.codex.json", "hooks.cursor.json"):
        assert "hooks/canvas-schema-check.sh" in (PLUGIN / "hooks" / name).read_text(), name


def test_privacy_check_names_the_processors_field():
    text = (PLUGIN / "skills" / "privacy-check" / "SKILL.md").read_text(encoding="utf-8")
    assert "`processors`" in text
    assert "A reassessment updates these same fields; it does not add a new block." in text
