"""Coverage tests for check_hook_delivery.py — did the harness run our hooks, or cancel them?

Branches: no transcript dir -> N/A rc 0; no outcomes -> quiet line; cancelled SessionStart -> FAIL
with timeout named, --strict exits 1; cancelled other hook -> WARN, --strict exits 0; all ok -> OK;
old transcript outside the window ignored; corrupt line skipped. In-process for the coverage floor.
"""

import json
import os
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _mod():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import check_hook_delivery

    return check_hook_delivery


def _run(project, home, capsys, *extra):
    rc = _mod().main(["--project-dir", str(project), "--claude-home", str(home), *extra])
    return rc, capsys.readouterr().out


def _transcript(home, project, name, events, age_days=0):
    tdir = _mod().transcript_dir(project, home)
    tdir.mkdir(parents=True, exist_ok=True)
    f = tdir / f"{name}.jsonl"
    f.write_text("\n".join(events) + "\n")
    if age_days:
        old = time.time() - age_days * 86400
        os.utime(f, (old, old))
    return f


def _att(kind, event, command, ts="2026-09-10T05:38:34.000Z", timeout=None):
    a = {"type": kind, "hookName": f"{event}:startup", "hookEvent": event, "command": command}
    if kind == "hook_cancelled":
        a.update({"durationMs": 5018, "timedOut": True, "timeoutMs": timeout or 5000})
    return json.dumps({"type": "attachment", "timestamp": ts, "attachment": a})


def test_no_transcript_dir_is_na(tmp_path, capsys):
    rc, out = _run(tmp_path / "proj", tmp_path / "home", capsys)
    assert rc == 0 and "N/A" in out


def test_cancelled_session_start_fails_and_names_timeout(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(
        home,
        proj,
        "s1",
        [
            _att("hook_success", "SessionStart", "Evidence link check"),
            _att("hook_cancelled", "SessionStart", "Mycelium feedback loop check"),
            "{not json",
            _att(
                "hook_cancelled",
                "SessionStart",
                "Mycelium feedback loop check",
                ts="2026-09-09T18:34:32.000Z",
            ),
        ],
    )
    rc, out = _run(proj, home, capsys)
    assert rc == 0
    assert (
        "hook-delivery FAIL: SessionStart | Mycelium feedback loop check: cancelled 2, ok 0" in out
    )
    assert "manifest timeout 5s" in out and "last cancelled 2026-09-10T05:38:34" in out
    assert "delivers NOTHING" in out
    rc, out = _run(proj, home, capsys, "--strict")
    assert rc == 1


def test_other_hook_cancelled_is_warn_not_strict_fail(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(home, proj, "s1", [_att("hook_cancelled", "Stop", "Mycelium stop check")])
    rc, out = _run(proj, home, capsys, "--strict")
    assert rc == 0 and "hook-delivery WARN: Stop | Mycelium stop check" in out


def test_all_ok_reports_ok(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(
        home, proj, "s1", [_att("hook_success", "SessionStart", "Mycelium feedback loop check")] * 3
    )
    rc, out = _run(proj, home, capsys)
    assert rc == 0 and "hook-delivery: OK — 3 hook run(s)" in out


def test_old_transcript_outside_window_is_ignored(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(
        home,
        proj,
        "old",
        [_att("hook_cancelled", "SessionStart", "Mycelium feedback loop check")],
        age_days=30,
    )
    rc, out = _run(proj, home, capsys, "--days", "7")
    assert rc == 0 and "no hook outcomes recorded" in out


# --- v0.204.0: the gate-block log has a reader --------------------------------------------


def _block_log(project, lines):
    d = project / ".claude" / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / "gate-block-log.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def test_gate_blocks_are_counted_per_session_and_reason(tmp_path, capsys):
    project = tmp_path / "p"
    now = "2026-09-14T10:00:00Z"
    _block_log(project, [
        {"ts": now, "hook": "gate.sh", "reason": "stale-stamp", "session_id": "s1"},
        {"ts": now, "hook": "gate.sh", "reason": "corrections-hash", "session_id": "s1"},
        {"ts": now, "hook": "gate.sh", "reason": "stale-stamp", "session_id": "s2"},
        {"ts": "2020-01-01T00:00:00Z", "hook": "gate.sh", "reason": "stale-stamp", "session_id": "old"},
    ])
    from datetime import UTC, datetime, timedelta
    line = _mod().gate_blocks(project, datetime.now(tz=UTC) - timedelta(days=3650))
    assert line.startswith("gate-block: 4 block(s) in 3 session(s)")
    line = _mod().gate_blocks(project, datetime(2026, 9, 1, tzinfo=UTC))
    assert line.startswith("gate-block: 3 block(s) in 2 session(s)")
    assert "corrections-hash 1, stale-stamp 2" in line


def test_no_log_is_reported_as_no_log_not_as_no_blocks(tmp_path, capsys):
    project = tmp_path / "p"
    project.mkdir()
    from datetime import UTC, datetime
    assert _mod().gate_blocks(project, datetime(2026, 9, 1, tzinfo=UTC)) is None
    rc, out = _run(project, tmp_path / "home", capsys)
    assert "no gate-block log" in out
    assert "not the same thing" in out


def test_unreadable_log_lines_are_counted_not_crashed_on(tmp_path):
    project = tmp_path / "p"
    d = project / ".claude" / "state"
    d.mkdir(parents=True)
    (d / "gate-block-log.jsonl").write_text('{"ts": "2026-09-14T10:00:00Z", "reason": "stale-stamp"}\nnot json\n{"no": "ts"}\n')
    from datetime import UTC, datetime
    line = _mod().gate_blocks(project, datetime(2026, 9, 1, tzinfo=UTC))
    assert "1 block(s)" in line
    assert "2 unreadable line(s) skipped" in line
