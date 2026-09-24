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


# In-process tests: the per-file coverage floor counts only what runs inside pytest's own process.
import importlib.util as _ilu  # noqa: E402
import io  # noqa: E402

_spec = _ilu.spec_from_file_location("canvas_write_check", PLUGIN / "scripts" / "canvas_write_check.py")
cwc = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(cwc)


def _main(monkeypatch, payload) -> str:
    monkeypatch.setattr("sys.stdin", io.StringIO(payload if isinstance(payload, str)
                                                 else json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert cwc.main() == 0
    return out.getvalue().strip()


def test_in_process_invalid_file_blocks(tmp_path, monkeypatch):
    _write(tmp_path, "canvas/privacy-assessment.yml", "reassessment: {}\n")
    got = _main(monkeypatch, {"tool_input": {"file_path": str(tmp_path / ".claude/canvas/privacy-assessment.yml")}})
    assert json.loads(got)["decision"] == "block"


def test_in_process_many_errors_are_capped(tmp_path, monkeypatch):
    keys = "".join(f"k{i}: 1\n" for i in range(12))
    _write(tmp_path, "diamonds/active.yml", "active_diamonds:\n" + "".join(
        f"  - id: d{i}\n    scale: L9\n    phase: nowhere\n" for i in range(6)) + keys)
    got = json.loads(_main(monkeypatch, {"tool_input": {"file_path": str(tmp_path / ".claude/diamonds/active.yml")}}))
    assert "more" in got["reason"]


def test_in_process_ignores_bad_input_and_other_paths(tmp_path, monkeypatch):
    assert _main(monkeypatch, "not json") == ""
    assert _main(monkeypatch, "[]") == ""
    assert _main(monkeypatch, {"tool_input": {}}) == ""
    assert _main(monkeypatch, {"tool_input": {"file_path": "notes.md"}}) == ""
    assert _main(monkeypatch, {"tool_input": {"file_path": str(tmp_path / ".claude/canvas/gone.yml")}}) == ""


def test_relative_paths_resolve_against_the_project(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert cwc._target({"tool_input": {"file_path": ".claude/canvas/x.yml"}}) == tmp_path / ".claude/canvas/x.yml"


def test_missing_dependencies_are_said_once_per_session(tmp_path, monkeypatch):
    _write(tmp_path, "canvas/purpose.yml", "why: x\n")
    monkeypatch.setattr(cwc, "_load_validator", lambda: (None, "missing jsonschema"))
    payload = {"session_id": "s9", "tool_input": {"file_path": str(tmp_path / ".claude/canvas/purpose.yml")}}
    first = json.loads(_main(monkeypatch, payload))
    assert "did not run" in first["hookSpecificOutput"]["additionalContext"]
    assert _main(monkeypatch, payload) == ""  # the same session is not told twice
    assert cwc._said_once(tmp_path, "") is False  # no session id: every write is its own session


def test_the_validator_loads_or_says_why():
    mod, why = cwc._load_validator()
    assert (mod is not None and why == "") or why.startswith("missing")
