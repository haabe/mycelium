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
            _att("hook_cancelled", "SessionStart", "Mycelium feedback loop check (fast tier)"),
            "{not json",
            _att(
                "hook_cancelled",
                "SessionStart",
                "Mycelium feedback loop check (fast tier)",
                ts="2026-09-09T18:34:32.000Z",
            ),
        ],
    )
    rc, out = _run(proj, home, capsys)
    assert rc == 0
    assert (
        "hook-delivery FAIL: SessionStart | Mycelium feedback loop check (fast tier): cancelled 2, ok 0" in out
    )
    assert "manifest timeout 5s" in out and "last cancelled 2026-09-10T05:38:34" in out
    assert "delivers NOTHING" in out
    rc, out = _run(proj, home, capsys, "--strict")
    assert rc == 1


def test_other_hook_cancelled_is_warn_not_strict_fail(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(home, proj, "s1", [_att("hook_cancelled", "Stop", "Mycelium next-action check")])
    rc, out = _run(proj, home, capsys, "--strict")
    assert rc == 0 and "hook-delivery WARN: Stop | Mycelium next-action check" in out


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


# --- retired labels: a hook renamed or split since is not a live FAIL ------------------------
# Dogfood 2026-10-02: "SessionStart | Mycelium feedback loop check" was split in v0.186.0 into
# "(fast tier)" and "(background tier)", and its old cancellations read as a FAIL for 30 days.

OLD = "Mycelium feedback loop check"
FAST = "Mycelium feedback loop check (fast tier)"
BACKGROUND = "Mycelium feedback loop check (background tier)"


def _manifest(tmp_path):
    m = tmp_path / "hooks.json"
    m.write_text(json.dumps({"hooks": {
        "SessionStart": [{"matcher": "startup", "hooks": [
            {"type": "command", "command": "bash fast.sh", "statusMessage": FAST},
            {"type": "command", "command": "bash bg.sh", "statusMessage": BACKGROUND},
            {"type": "command", "command": "bash contract-part.sh 1"},
        ]}],
        "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "bash stop.sh"}]}],
    }}))
    return m


def _split_transcript(home, proj, *, current_cancelled=False):
    events = [
        _att("hook_cancelled", "SessionStart", OLD, ts="2026-09-09T18:34:32.000Z"),
        _att("hook_success", "SessionStart", OLD, ts="2026-09-10T05:00:00.000Z"),
        _att("hook_cancelled", "SessionStart", OLD, ts="2026-09-10T05:38:34.000Z"),
        _att("hook_success", "SessionStart", FAST, ts="2026-09-12T08:00:00.000Z"),
        _att("hook_success", "SessionStart", FAST, ts="2026-09-13T08:00:00.000Z"),
        _att("hook_success", "SessionStart", BACKGROUND, ts="2026-09-13T08:00:00.000Z"),
    ]
    if current_cancelled:
        events.append(_att("hook_cancelled", "SessionStart", FAST, ts="2026-09-14T08:00:00.000Z"))
    _transcript(home, proj, "s1", events)


def test_cancelled_retired_label_is_warn_with_last_seen_and_current_counts(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _split_transcript(home, proj)
    rc, out = _run(proj, home, capsys, "--strict", "--days", "30",
                   "--hooks-manifest", str(_manifest(tmp_path)))
    assert rc == 0
    assert "hook-delivery FAIL" not in out
    assert f"hook-delivery WARN (retired label): SessionStart | {OLD}: cancelled 2, ok 1" in out
    assert "last seen 2026-09-10" in out and "leaves the 30-day window on 2026-10-10" in out
    assert (f"hook-delivery current labels of SessionStart in the last 30 day(s): "
            f"{BACKGROUND}: ok 1, cancelled 0, error 0; {FAST}: ok 2, cancelled 0, error 0") in out


def test_cancelled_current_label_still_fails_beside_a_retired_one(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _split_transcript(home, proj, current_cancelled=True)
    rc, out = _run(proj, home, capsys, "--strict", "--days", "30",
                   "--hooks-manifest", str(_manifest(tmp_path)))
    assert rc == 1
    assert f"hook-delivery FAIL: SessionStart | {FAST}: cancelled 1, ok 2" in out
    assert f"hook-delivery WARN (retired label): SessionStart | {OLD}" in out
    assert "current labels of SessionStart" in out


def test_label_without_status_message_is_matched_by_command(tmp_path, capsys):
    mod = _mod()
    labels = mod.current_labels(_manifest(tmp_path))
    assert not mod.is_retired("SessionStart | bash contract-part.sh 1", labels)
    assert not mod.is_retired("SessionStart:startup | " + FAST, labels)  # hookName fallback
    assert mod.is_retired("PreCompact | anything", labels)  # an event the manifest dropped
    assert not mod.is_retired("? | bash stop.sh", labels)
    assert mod.is_retired("? | gone", labels)


def test_unreadable_manifest_treats_every_label_as_current(tmp_path, capsys):
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _split_transcript(home, proj)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert _mod().current_labels(bad) is None
    assert _mod().current_labels(tmp_path / "missing.json") is None
    rc, out = _run(proj, home, capsys, "--strict", "--days", "30", "--hooks-manifest", str(bad))
    assert rc == 1 and f"hook-delivery FAIL: SessionStart | {OLD}" in out
    assert "retired" not in out and "current labels of" not in out


def test_shipped_manifest_retires_the_pre_split_session_start_label(tmp_path, capsys):
    """The default manifest is the plugin's own hooks.json: the 0.186.0 split is in it."""
    mod = _mod()
    labels = mod.current_labels(mod.DEFAULT_MANIFEST)
    assert labels is not None
    assert mod.is_retired(f"SessionStart | {OLD}", labels)
    assert not mod.is_retired(f"SessionStart | {FAST}", labels)


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


# --- v0.213.0: runtime manifests --------------------------------------------------------


def test_runtime_dirs_report_manifest_presence_and_absent_dirs_say_nothing(tmp_path):
    project = tmp_path / "p"
    (project / ".codex").mkdir(parents=True)
    (project / ".cursor").mkdir()
    (project / ".cursor" / "hooks.json").write_text("{}")
    lines = _mod().runtime_manifests(project)
    assert len(lines) == 2
    assert any("NO hooks.json" in x and "codex" in x for x in lines)
    assert any("present" in x and "cursor" in x for x in lines)
    assert _mod().runtime_manifests(tmp_path / "none") == []


# --- mutation sample 2026-10-11 (seed 20260910): lines no test constrained ----------------
# The clean paths' severity 0 (as 1), the window edges (`<` as `<=`, twice), the event name falling
# back to hookName (`or` as `and`), a non-hook attachment skipped (`or` as `and`), and a missing
# timestamp leaving last_seen unset (`and` as `or`). Two survivors are equivalent and have no test:
# `ts > last_seen` and `ts > last_cancelled` as `>=` assign the same value when the two are equal.

def _utc():
    from datetime import timezone
    return timezone.utc


def test_the_clean_answers_carry_severity_0():
    m = _mod()
    sev, lines = m.report({}, 7, "SessionStart")
    assert sev == 0 and "no hook outcomes recorded" in lines[0]
    ok = {"SessionStart | x": {"ok": 3, "cancelled": 0, "error": 0, "last_cancelled": None,
                               "timeout_ms": None, "last_seen": None}}
    sev, lines = m.report(ok, 7, "SessionStart")
    assert sev == 0 and lines[0].startswith("hook-delivery: OK")


def test_a_transcript_written_at_the_window_edge_is_read(tmp_path):
    from datetime import datetime
    m = _mod()
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    f = _transcript(home, proj, "s1", [_att("hook_success", "SessionStart", "c")])
    edge = datetime.fromtimestamp(f.stat().st_mtime, tz=_utc())
    assert m.scan(m.transcript_dir(proj, home), edge)["SessionStart | c"]["ok"] == 1


def test_a_gate_block_at_the_window_edge_is_counted(tmp_path):
    from datetime import datetime
    project = tmp_path / "p"
    _block_log(project, [{"ts": "2026-09-14T10:00:00+00:00", "reason": "stale-stamp",
                          "session_id": "s1"}])
    line = _mod().gate_blocks(project, datetime(2026, 9, 14, 10, tzinfo=_utc()))
    assert line.startswith("gate-block: 1 block(s) in 1 session(s)")


def test_with_no_hook_event_the_key_falls_back_to_the_hook_name(tmp_path):
    m = _mod()
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    a = {"type": "hook_success", "hookName": "SessionStart:startup", "command": "c"}
    _transcript(home, proj, "s1", [json.dumps({"timestamp": "2026-09-10T05:00:00Z",
                                               "attachment": a})])
    from datetime import datetime
    per = m.scan(m.transcript_dir(proj, home), datetime(2000, 1, 1, tzinfo=_utc()))
    assert list(per) == ["SessionStart:startup | c"]


def test_an_attachment_that_is_not_a_hook_outcome_is_skipped(tmp_path):
    m = _mod()
    proj, home = tmp_path / "proj", tmp_path / "home"
    proj.mkdir()
    _transcript(home, proj, "s1", [
        json.dumps({"note": "mentions hook_success", "attachment": {"type": "file"}}),
        json.dumps({"note": "mentions hook_success", "attachment": "hook_success"}),
        _att("hook_success", "Stop", "c"),
    ])
    from datetime import datetime
    per = m.scan(m.transcript_dir(proj, home), datetime(2000, 1, 1, tzinfo=_utc()))
    assert list(per) == ["Stop | c"] and per["Stop | c"]["ok"] == 1


def test_an_outcome_with_no_timestamp_leaves_last_seen_unset():
    m = _mod()
    row = {"ok": 0, "cancelled": 0, "error": 0, "last_cancelled": None, "timeout_ms": None,
           "last_seen": None}
    m._tally(row, {}, {"type": "hook_success"})
    assert row["ok"] == 1 and row["last_seen"] is None
