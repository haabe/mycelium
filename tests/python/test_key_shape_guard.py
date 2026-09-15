"""Coverage for key_shape_guard: the write-time half of the near-duplicate-keys row.

WAYS THIS COULD ROT:
  1. IT FIRES ON THE CONVENTION IT RECOMMENDS. The `notes[] - date:` form puts the date in
     a VALUE; a guard that flags it teaches the author the wrong lesson.
  2. IT DISAGREES WITH THE SWEEP. Same two regexes, same stem function, or the author is
     warned at the keystroke about something the sweep later says is fine (or vice versa).
  3. IT FIRES ON A RE-WRITE OF AN EXISTING KEY. An Edit that touches `reply_sent` in a file
     that has `reply_sent` is not a new spelling.
  4. IT BLOCKS. Advisory only; exit 0 always, and a broken payload is silence.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts"
SCRIPT = SCRIPTS / "key_shape_guard.py"


def _mod():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("key_shape_guard", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(payload, env=None):
    return subprocess.run([sys.executable, str(SCRIPT)], input=payload,
                          capture_output=True, text=True, check=False, env=env)


def _payload(path, text, tool="Write"):
    key = "content" if tool == "Write" else "new_string"
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": str(path), key: text}})


def _warn(path, text, tool="Write", env=None):
    r = _run(_payload(path, text, tool), env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"] if r.stdout.strip() else ""


# ---------------------------------------------------------------- happy


def test_plain_keys_and_the_notes_form_are_silent(tmp_path):
    canvas = tmp_path / ".claude/canvas/human-tasks.yml"
    text = ("- id: ht-001\n  status: open\n  notes:\n    - date: 2026-09-15\n"
            "      kind: reply_sent\n      note: \"sent\"\n  stored_at: '2026-09-15'\n")
    assert _warn(canvas, text) == ""


def test_rewriting_an_existing_key_is_not_a_new_spelling(tmp_path):
    canvas = tmp_path / ".claude/canvas/human-tasks.yml"
    canvas.parent.mkdir(parents=True)
    canvas.write_text("- id: ht-001\n  reply_sent: false\n")
    assert _warn(canvas, "  reply_sent: true\n", tool="Edit") == ""


# ---------------------------------------------------------------- sad


def test_a_dated_key_fires_and_names_the_plain_key(tmp_path):
    canvas = tmp_path / ".claude/canvas/human-tasks.yml"
    out = _warn(canvas, "- id: ht-001\n  reply_sent_2026_09_20: yes\n")
    assert "reply_sent_2026_09_20" in out
    assert "the plain key is `reply_sent`" in out
    assert "notes:" in out


def test_an_entity_scoped_key_fires(tmp_path):
    out = _warn(tmp_path / ".claude/diamonds/active.yml", "ht_010_status: done\n")
    assert "ht_010_status" in out


def test_a_second_spelling_of_an_existing_stem_fires(tmp_path):
    canvas = tmp_path / ".claude/canvas/human-tasks.yml"
    canvas.parent.mkdir(parents=True)
    canvas.write_text("- id: ht-001\n  reply_sent: false\n")
    out = _warn(canvas, "  reply-sent: true\n", tool="Edit")
    assert "`reply-sent:` is a new spelling" in out
    assert "`reply_sent`" in out


def test_multiedit_is_read(tmp_path):
    payload = json.dumps({"tool_name": "MultiEdit", "tool_input": {
        "file_path": str(tmp_path / ".claude/canvas/opportunities.yml"),
        "edits": [{"old_string": "x", "new_string": "  promoted_2026_09_02: true\n"}]}})
    r = _run(payload)
    assert "promoted_2026_09_02" in r.stdout


def test_a_fire_is_logged(tmp_path):
    import os
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path))
    _warn(tmp_path / ".claude/canvas/purpose.yml", "scope_correction_2026_08_27: x\n", env=env)
    log = tmp_path / ".claude/state/key-shape-guard-log.jsonl"
    assert log.exists()
    assert json.loads(log.read_text().splitlines()[0])["hook"] == "key-shape-guard"


# ---------------------------------------------------------------- bad


def test_unwatched_paths_and_broken_payloads_are_silent(tmp_path):
    assert _warn(tmp_path / "docs/notes.md", "promoted_2026_09_02: true\n") == ""
    assert _warn(tmp_path / ".claude/memory/notes.md", "promoted_2026_09_02: true\n") == ""
    r = _run("not json")
    assert r.returncode == 0 and r.stdout == ""


def test_bare_date_keys_are_left_to_nobody_on_purpose():
    """YAML reads `2026-06-11:` as a date, so the sweep cannot see it; the guard matches."""
    m = _mod()
    assert m.findings("remediation_history:\n  2026-06-11: refreshed\n") == []


def test_guard_and_sweep_agree_on_the_regexes():
    m = _mod()
    hits = m.findings("horizon_set_2026_08_28: x\ncomp-107_note: y\nplain: z\n")
    assert len(hits) == 2
    assert m.findings("plain-key: z\n", {"plain_key": {"plain_key"}})
    assert not m.findings("plain_key: z\n", {"plain_key": {"plain_key"}})


def test_case_only_variants_are_left_to_the_sweep():
    m = _mod()
    assert m.findings("Date: x\n", {"date": {"date"}}) == []


def test_prose_inside_a_block_scalar_or_quoted_string_is_not_a_key():
    m = _mod()
    text = ('- id: ht-001\n  summary: >-\n    Date: 2026-09-14 was the day.\n    CLASSIFICATION: strong\n'
            '  detail: "first line\n    Action: read the chapter\n    done"\n  status: open\n')
    assert m.keys_in(text) == ["id", "summary", "detail", "status"]


def test_writing_the_plain_spelling_beside_a_dated_twin_is_the_fix_not_a_finding():
    m = _mod()
    assert m.findings("posted: true\n", {"posted": {"POSTED_2026_08_10"}}) == []


# ---------------------------------------------------------------- in-process (coverage of the hook path)


def _payload_dict(path, text, tool="Write"):
    key = "content" if tool == "Write" else "new_string"
    return {"tool_name": tool, "tool_input": {"file_path": str(path), key: text}}


def test_scan_for_reads_the_target_file_and_ignores_unwatched_paths(tmp_path):
    m = _mod()
    canvas = tmp_path / ".claude/canvas/human-tasks.yml"
    canvas.parent.mkdir(parents=True)
    canvas.write_text("- id: ht-001\n  reply_sent: false\n  nested:\n    - deep_key: 1\n")
    assert m.scan_for(_payload_dict(canvas, "  reply-sent: true\n", "Edit"))
    assert m.scan_for(_payload_dict(tmp_path / "docs/x.md", "reply-sent: true\n")) == []
    assert m.scan_for({"tool_name": "Write", "tool_input": "not a dict"}) == []
    assert m.scan_for(_payload_dict(canvas, "   \n")) == []
    assert "deep_key" in m._file_spellings(str(canvas))
    assert m._file_spellings(str(tmp_path / "missing.yml")) == {}


def test_main_prints_the_advisory_and_logs_in_process(tmp_path, monkeypatch, capsys):
    import io
    m = _mod()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    hits = "\n".join(f"  k{i}_2026_09_{10 + i}: x" for i in range(7))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        _payload_dict(tmp_path / ".claude/canvas/purpose.yml", hits + "\n"))))
    assert m.main() == 0
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "and 2 more in this write" in out and "notes:" in out
    assert (tmp_path / ".claude/state/key-shape-guard-log.jsonl").exists()
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert m.main() == 0 and capsys.readouterr().out == ""
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        _payload_dict(tmp_path / ".claude/canvas/purpose.yml", "plain: 1\n"))))
    assert m.main() == 0 and capsys.readouterr().out == ""
