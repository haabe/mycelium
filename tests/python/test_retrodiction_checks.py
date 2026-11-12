"""The two deterministic retrodiction cases, said at the write that is their moment.

WHAT WAS WRONG. Every hook is a script, and a blind-scored retrodiction over the corrections the
founder caught by hand found two a script reading existing files could have caught, which no
script did: an instrument frozen for diamond X while a human task on X was in flight (dogfood
2026-08-21), and a day of acquisition work that never opened go-to-market.yml's channel map
(dogfood 2026-08-25). FOUNDER RULING 2026-11-12, "Scripts for two cases": both are wired as
scripts; no model-evaluated hook.

  check_concurrent_instrument.py  on a write to .claude/evals/assumption-tests/*.md
  check_channel_map_read.py       on a write to .claude/canvas/human-tasks.yml
Both run from hooks/post-write-nudge.sh. Advisory: neither ever blocks.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
HOOK = ROOT / "plugins" / "mycelium" / "hooks" / "post-write-nudge.sh"
sys.path.insert(0, str(SCRIPTS))

import check_channel_map_read as ccm  # noqa: E402
import check_concurrent_instrument as cci  # noqa: E402

SESSION = "sess-1"
TASKS = """pending_tasks:
- id: ht-007
  type: outreach
  status: waiting
  diamond_ref: l1-strategy
  horizon: '2026-08-30'
  objective: five replies sent to builders who stated the moment; score at two weeks
- id: ht-008
  type: outreach
  status: pending
  diamond_ref: l2-x
  objective: ask three maintainers how they triage
- id: ht-009
  type: observation
  status: in_progress
  diamond_ref: l3-y
  objective: watch a session
"""


def _project(tmp_path: Path, *, gtm: bool = True) -> Path:
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "human-tasks.yml").write_text(TASKS)
    if gtm:
        (canvas / "go-to-market.yml").write_text("channel_intelligence:\n  talk_2026_05_07: worked\n")
    (tmp_path / ".claude" / "evals" / "assumption-tests").mkdir(parents=True)
    (tmp_path / ".claude" / "state").mkdir()
    return tmp_path


def _instrument(project: Path, header: str, body: str = "## Prediction\nI expect 3.\n") -> Path:
    path = project / ".claude" / "evals" / "assumption-tests" / "2026-08-21-sweep.md"
    path.write_text(f"---\ntype: assumption-test\n{header}---\n\n{body}")
    return path


def _hook(project: Path, payload: dict) -> str:
    env = {"CLAUDE_PROJECT_DIR": str(project),
           "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin"}
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, check=False, env=env, cwd=project).stdout


def _main(module, monkeypatch, capsys, payload) -> str:
    monkeypatch.setattr(sys, "stdin", io.StringIO(
        payload if isinstance(payload, str) else json.dumps(payload)))
    assert module.main() == 0
    return capsys.readouterr().out


# ------------------------------------------------- case 1: an instrument already in flight


def test_an_instrument_for_a_diamond_with_one_in_flight_is_named(tmp_path):
    """RED ON THE OLD CODE: nothing read the instrument and human-tasks.yml together."""
    project = _project(tmp_path)
    path = _instrument(project, "status: live   # live | scored\ndiamond_ref: l1-strategy\n")
    out = _hook(project, {"tool_name": "Write", "session_id": SESSION,
                          "tool_input": {"file_path": str(path), "content": path.read_text()}})
    assert "INSTRUMENT ALREADY IN FLIGHT ON THIS DIAMOND" in out
    assert "ht-007 (waiting, horizon 2026-08-30, diamond_ref l1-strategy)" in out


def test_a_diamond_anchor_in_the_body_names_the_diamond_too(tmp_path):
    project = _project(tmp_path)
    body = "Tests the [target -> diamonds/active.yml#l1-strategy.blockers] gap.\n"
    findings = cci.findings(project, _instrument(project, "status: live\n", body).read_text())
    assert findings and findings[0].startswith("ht-007 (waiting")


@pytest.mark.parametrize(("header", "body"), [
    ("status: live\ndiamond_ref: l9-other\n", ""),            # no task in flight on this diamond
    ("status: scored\ndiamond_ref: l1-strategy\n", ""),       # not a live design any more
    ("status: live\n", ""),                                   # names no diamond: not checked
    ("status: live\ndiamond_ref: l1-strategy\n",              # the reason is written, task named
     "Runs beside ht-007 because it reads a different population.\n"),
])
def test_an_instrument_with_nothing_in_flight_on_its_diamond_is_silent(tmp_path, header, body):
    project = _project(tmp_path)
    assert cci.findings(project, _instrument(project, header, body).read_text()) == []


def test_a_pending_or_watching_task_is_not_in_flight(tmp_path):
    project = _project(tmp_path)
    assert cci.findings(project, _instrument(project, "status: live\ndiamond_ref: l2-x\n")
                        .read_text()) == []


def test_main_reads_relative_paths_and_fails_open(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    _instrument(project, "status: live\ndiamond_ref: l1-strategy\n")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    rel = ".claude/evals/assumption-tests/2026-08-21-sweep.md"
    assert "ht-007" in _main(cci, monkeypatch, capsys, {"tool_input": {"file_path": rel}})
    assert _main(cci, monkeypatch, capsys, "not json") == ""
    assert _main(cci, monkeypatch, capsys, {"tool_input": {"file_path": "notes.md"}}) == ""
    assert _main(cci, monkeypatch, capsys, {"tool_input": {}}) == ""
    gone = ".claude/evals/assumption-tests/missing.md"
    assert _main(cci, monkeypatch, capsys, {"tool_input": {"file_path": gone}}) == ""


def test_no_human_tasks_file_means_nothing_in_flight(tmp_path):
    project = _project(tmp_path)
    text = _instrument(project, "status: live\ndiamond_ref: l1-strategy\n").read_text()
    (project / ".claude" / "canvas" / "human-tasks.yml").unlink()
    assert cci.findings(project, text) == []


def test_without_the_header_parser_only_anchors_are_read(monkeypatch):
    monkeypatch.setitem(sys.modules, "check_instrument_contract", None)
    ids, status = cci.instrument_diamonds("---\ndiamond_ref: l1\n---\ndiamonds/active.yml#l2\n")
    assert ids == {"l2"} and status == ""


# ------------------------------------------------- case 2: outreach before the channel map


def _log(project: Path, *rows: dict) -> None:
    with (project / ".claude" / "state" / "read-log.jsonl").open("a") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def _tasks_write(project: Path, new_string: str, session: str = SESSION) -> dict:
    return {"tool_name": "Edit", "session_id": session, "tool_input": {
        "file_path": str(project / ".claude" / "canvas" / "human-tasks.yml"),
        "old_string": "x", "new_string": new_string}}


def test_starting_outreach_without_reading_the_channel_map_is_named(tmp_path):
    """RED ON THE OLD CODE: handoff step 1b said it in prose and nothing checked it."""
    project = _project(tmp_path)
    _log(project, {"file_path": str(project / ".claude/canvas/go-to-market.yml"),
                   "session_id": "an-earlier-session"})
    out = _hook(project, _tasks_write(project, "- id: ht-008\n  type: outreach\n"))
    assert "CHANNEL MAP NOT READ THIS SESSION" in out and "ht-008" in out
    assert "Human tasks canvas edited" in out            # the canvas nudge still rides along


def test_the_note_is_not_muted_by_the_once_per_session_canvas_ledger(tmp_path):
    project = _project(tmp_path)
    _hook(project, _tasks_write(project, "- id: ht-009\n  note: unrelated\n"))   # ledger entry
    out = _hook(project, _tasks_write(project, "- id: ht-008\n  type: outreach\n"))
    assert "CHANNEL MAP NOT READ THIS SESSION" in out
    assert "Human tasks canvas edited" not in out


@pytest.mark.parametrize("read_by", ["Read", "Bash"])
def test_a_channel_map_read_this_session_silences_it(tmp_path, read_by):
    project = _project(tmp_path)
    row = {"tool": read_by, "file_path": str(project / ".claude/canvas/go-to-market.yml"),
           "session_id": SESSION}
    if read_by == "Bash":
        row["inferred"] = True
    _log(project, {"file_path": "x", "session_id": SESSION}, row)
    assert ccm.findings(project, SESSION, "- id: ht-008\n  type: outreach\n") == []


@pytest.mark.parametrize("written", [
    "- id: ht-007\n  type: outreach\n",     # waiting: already sent, this is not its start
    "- id: ht-009\n  type: outreach?\n",    # ht-009 is an observation, whatever the text says
    "- id: ht-100\n  type: outreach\n",     # no such task in the file
    "- id: ht-009\n  note: x\n",            # the write says nothing about outreach
])
def test_a_write_that_starts_no_outreach_is_silent(tmp_path, written):
    assert ccm.findings(_project(tmp_path), SESSION, written) == []


def test_an_unread_channel_map_with_reads_of_other_files_still_names_the_task(tmp_path):
    project = _project(tmp_path)
    _log(project, {"file_path": str(project / ".claude/canvas/human-tasks.yml"),
                   "session_id": SESSION})
    findings = ccm.findings(project, SESSION, "- id: ht-008\n  type: outreach\n")
    assert findings == ["ht-008"]


def test_no_channel_map_or_no_session_id_is_silent(tmp_path):
    written = "- id: ht-008\n  type: outreach\n"
    assert ccm.findings(_project(tmp_path, gtm=False), SESSION, written) == []
    assert ccm.findings(_project(tmp_path / "b"), "", written) == []


def test_ccm_main_reads_relative_paths_and_fails_open(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    (project / ".claude" / "state" / "read-log.jsonl").write_text("not json go-to-market.yml sess-1\n")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project))
    payload = {"session_id": SESSION, "tool_input": {
        "file_path": ".claude/canvas/human-tasks.yml",
        "edits": [{"new_string": "- id: ht-008\n  type: outreach\n"}]}}
    assert "ht-008" in _main(ccm, monkeypatch, capsys, payload)
    assert _main(ccm, monkeypatch, capsys, "not json") == ""
    assert _main(ccm, monkeypatch, capsys, {"tool_input": {"file_path": "x.yml"}}) == ""
    assert _main(ccm, monkeypatch, capsys, {"tool_input": {}}) == ""
