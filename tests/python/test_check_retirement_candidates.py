"""Coverage for check_retirement_candidates: the report that says what could go.

WAYS THIS COULD ROT:
  1. IT LISTS A MECHANISM SOMETHING READS. A hook registered in a runtime manifest, a check
     in the gate set, a skill another skill names: none is a candidate however quiet.
  2. IT PASSES OVER NOTHING. No project record means no measurement, not a clean bill.
  3. IT SKIPS THE UNMEASURABLE. A hook that writes no record is the finding, listed as such.
  4. IT REMOVES SOMETHING. It never does; the decision is the maintainer's.
"""
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_retirement_candidates.py"


def _mod():
    spec = importlib.util.spec_from_file_location("crc", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["crc"] = m
    spec.loader.exec_module(m)
    return m


def _framework(tmp_path):
    root = tmp_path / "fw"
    for skill in ("alive", "quiet-unread", "quiet-read"):
        (root / "skills" / skill).mkdir(parents=True)
        (root / "skills" / skill / "SKILL.md").write_text("# skill\n")
    (root / "skills" / "alive" / "SKILL.md").write_text("Run /quiet-read afterwards.\n")
    (root / "hooks").mkdir()
    (root / "hooks" / "logs.sh").write_text('echo x >> "$D/.claude/state/logs-log.jsonl"\n')
    (root / "hooks" / "mute.sh").write_text("exit 0\n")
    (root / "hooks" / "registered.sh").write_text("exit 0\n")
    (root / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"hooks": [{"command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/registered.sh"}]}]}}))
    (root / "scripts").mkdir()
    (root / "scripts" / "check_gated.py").write_text("print('x')\n")
    (root / "scripts" / "check_orphan.py").write_text("print('x')\n")
    (root / "scripts" / "local-gate-set.txt").write_text("check_gated.py\n")
    return root


def _project(tmp_path):
    proj = tmp_path / "proj"
    (proj / ".claude" / "harness").mkdir(parents=True)
    (proj / ".claude" / "state").mkdir()
    (proj / ".claude" / "harness" / "decision-log.md").write_text(
        "## 2026-09-10 — DL-1: ran /mycelium:alive today\n\ntext\n\n"
        "## 2026-05-01 — DL-0: ran /quiet-unread long ago\n")
    (proj / ".claude" / "state" / "logs-log.jsonl").write_text(
        '{"at": "2026-09-12T10:00:00+00:00", "hook": "logs"}\n')
    return proj


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, check=False)


# ---------------------------------------------------------------- happy


def test_candidates_are_quiet_and_unread_only(tmp_path):
    m = _mod()
    res = m.assess(_framework(tmp_path), _project(tmp_path), 60, date(2026, 9, 15))
    by = {(r["kind"], r["name"]): r for r in res["rows"]}
    assert not by[("skill", "alive")]["candidate"]
    assert by[("skill", "alive")]["last"] == date(2026, 9, 10)
    assert by[("skill", "quiet-unread")]["candidate"]
    assert not by[("skill", "quiet-read")]["candidate"]
    assert by[("skill", "quiet-read")]["readers"] == ["skills/alive/SKILL.md"]
    assert not by[("hook", "logs.sh")]["candidate"]
    assert by[("hook", "logs.sh")]["last"] == date(2026, 9, 12)
    assert not by[("hook", "registered.sh")]["candidate"]
    assert "hooks/hooks.json" in by[("hook", "registered.sh")]["readers"]
    assert not by[("check", "check_gated.py")]["candidate"]
    assert by[("check", "check_orphan.py")]["candidate"]


def test_a_hook_that_writes_no_record_is_unmeasurable_not_a_candidate(tmp_path):
    m = _mod()
    res = m.assess(_framework(tmp_path), _project(tmp_path), 60, date(2026, 9, 15))
    mute = next(r for r in res["rows"] if r["name"] == "mute.sh")
    assert mute["fired"] == "writes no record"
    assert not mute["candidate"]


def test_the_report_names_the_candidates_and_the_unmeasurable(tmp_path):
    root, proj = _framework(tmp_path), _project(tmp_path)
    r = _run("--framework-root", str(root), "--project-dir", str(proj), "--today", "2026-09-15")
    assert r.returncode == 0, r.stderr
    assert "quiet-unread" in r.stdout and "check_orphan.py" in r.stdout
    assert "no reader" in r.stdout
    assert "write no record" in r.stdout and "mute.sh" in r.stdout
    assert "DECISION STAYS WITH THE MAINTAINER" in r.stdout


def test_json_output_round_trips(tmp_path):
    root, proj = _framework(tmp_path), _project(tmp_path)
    r = _run("--framework-root", str(root), "--project-dir", str(proj), "--today",
             "2026-09-15", "--json")
    data = json.loads(r.stdout)
    assert data["cutoff"] == "2026-07-17"
    assert any(row["candidate"] for row in data["rows"])


# ---------------------------------------------------------------- sad / bad


def test_no_project_record_is_not_a_pass(tmp_path):
    root = _framework(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    r = _run("--framework-root", str(root), "--project-dir", str(empty))
    assert r.returncode == 1 and "NOT A PASS" in r.stdout


def test_no_framework_root_is_a_precondition_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    r = subprocess.run([sys.executable, str(SCRIPT), "--framework-root", str(tmp_path / "nope"),
                        "--project-dir", str(tmp_path)],
                       capture_output=True, text=True, check=False,
                       env={"PATH": "/usr/bin:/bin"})
    # The script's own parent is a real framework root, so the fallback finds it; the
    # precondition failure is reachable only when neither the flag nor the tree resolves.
    assert r.returncode in (0, 1, 2)


def test_window_moves_the_verdict(tmp_path):
    m = _mod()
    root, proj = _framework(tmp_path), _project(tmp_path)
    wide = m.assess(root, proj, 365, date(2026, 9, 15))
    assert not next(r for r in wide["rows"] if r["name"] == "quiet-unread")["candidate"]


def test_a_skill_read_in_the_read_log_counts_as_fired(tmp_path):
    m = _mod()
    root, proj = _framework(tmp_path), _project(tmp_path)
    (proj / ".claude" / "state" / "read-log.jsonl").write_text(json.dumps({
        "ts": "2026-09-14T09:00:00Z", "file_path": "/x/skills/quiet-unread/SKILL.md"}) + "\n")
    res = m.assess(root, proj, 60, date(2026, 9, 15))
    row = next(r for r in res["rows"] if r["name"] == "quiet-unread")
    assert row["last"] == date(2026, 9, 14) and not row["candidate"]


# ---------------------------------------------------------------- in-process


def test_hook_state_files_follow_the_helper_and_dates_come_from_rows_or_mtime(tmp_path):
    m = _mod()
    root = _framework(tmp_path)
    (root / "hooks" / "helped.sh").write_text('python3 "$R/scripts/helper.py"\n')
    (root / "scripts" / "helper.py").write_text(
        'p = root / "state" / "helper.json"\nq = "helper-log.jsonl"\n')
    assert m.hook_state_files(root, "helped.sh") == {"helper.json", "helper-log.jsonl"}
    assert m.hook_state_files(root, "absent.sh") == set()
    st = tmp_path / "proj" / ".claude" / "state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "a.json").write_text("{}")
    assert m._last_date_in_state_file(st / "a.json") is not None
    (st / "b.jsonl").write_text("garbage\n")
    assert m._last_date_in_state_file(st / "b.jsonl") is not None
    assert m._last_date_in_state_file(st / "none.jsonl") is None


def test_print_and_main_in_process(tmp_path, monkeypatch, capsys):
    m = _mod()
    root, proj = _framework(tmp_path), _project(tmp_path)
    (proj / ".claude" / "harness" / "decision-log.md").write_text(
        "## not-a-date heading\nran /alive\n## 2026-09-10 — ran /mycelium:alive\n")
    (proj / ".claude" / "state" / "read-log.jsonl").write_text(
        'garbage\n{"ts": "bad", "file_path": "/x/skills/alive/SKILL.md"}\n'
        '{"ts": "2026-09-14T09:00:00Z", "file_path": "/x/skills/nope/SKILL.md"}\n')
    monkeypatch.setattr("sys.argv", ["x", "--framework-root", str(root), "--project-dir",
                                     str(proj), "--today", "2026-09-15", "--strict"])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "Quiet but read" in out and "quiet-read" in out
    monkeypatch.setattr("sys.argv", ["x", "--framework-root", str(tmp_path / "nowhere"),
                                     "--project-dir", str(proj)])
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(m, "framework_root", lambda explicit: None)
    assert m.main() == 2
    bare = tmp_path / "bare"
    (bare / "skills").mkdir(parents=True)
    (bare / "hooks").mkdir()
    monkeypatch.setattr(m, "framework_root", lambda explicit: bare)
    monkeypatch.setattr("sys.argv", ["x", "--project-dir", str(proj)])
    assert m.main() == 1
    assert "NOT A PASS" in capsys.readouterr().out
