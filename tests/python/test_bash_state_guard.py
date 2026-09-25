"""Shell commands that change canvas or diamond state are judged like edits are (v0.253.2).

E2E run 24 wrote `privacy-assessment.yml` through a shell command and the schema check never saw
it; the scale-lock gate was likewise registered on the edit tools only, so a shell write to
diamonds/active.yml skipped the entry locks, the phase-move gates and the ruling record.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
_spec = importlib.util.spec_from_file_location("bash_state_guard",
                                               PLUGIN / "scripts" / "bash_state_guard.py")
bsg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsg)


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text("active_diamonds: []\n")
    return tmp_path


def _pre(root: Path, cmd: str) -> int:
    return bsg.pre({"tool_input": {"command": cmd}}, root)


PY_WRITE = ('python3 -c "from pathlib import Path; '
            "Path('.claude/diamonds/active.yml').write_text('x')\"")
CLOSING_PATH = ("python3 scripts/derive_closing_path.py --diamond d1 --write "
                ".claude/diamonds/active.yml")


def test_shell_writes_to_the_diamond_file_are_refused(tmp_path, capsys):
    root = _project(tmp_path)
    for cmd in ("sed -i '' 's/discover/develop/' .claude/diamonds/active.yml",
                "echo 'active_diamonds: []' > .claude/diamonds/active.yml",
                PY_WRITE):
        assert _pre(root, cmd) == 2, cmd
    assert "Edit or Write" in capsys.readouterr().err


def test_reads_and_mycelium_own_writer_are_allowed(tmp_path):
    root = _project(tmp_path)
    for cmd in ("cat .claude/diamonds/active.yml", "grep phase .claude/diamonds/active.yml",
                "python3 -c \"import yaml; yaml.safe_load(open('.claude/diamonds/active.yml'))\"",
                CLOSING_PATH, "ls"):
        assert _pre(root, cmd) == 0, cmd


def test_pre_snapshots_the_diamond_file(tmp_path):
    root = _project(tmp_path)
    assert _pre(root, "ls") == 0
    state = root / bsg.STATE_REL
    assert (state / "active.yml.before").read_text() == "active_diamonds: []\n"
    assert float((state / "stamp").read_text()) > 0


def _post(root: Path, capsys) -> str:
    assert bsg.post({"session_id": "s1"}, root) == 0
    return capsys.readouterr().out.strip()


def _age(path: Path, seconds: float) -> None:
    t = time.time() + seconds
    os.utime(path, (t, t))


def test_an_invalid_canvas_file_written_by_the_shell_is_named(tmp_path, capsys):
    root = _project(tmp_path)
    _pre(root, "ls")
    f = root / ".claude" / "canvas" / "privacy-assessment.yml"
    f.write_text("open_blockers: [x]\n")
    _age(f, 5)
    out = json.loads(_post(root, capsys))
    assert out["decision"] == "block" and "'open_blockers' was unexpected" in out["reason"]


def test_a_diamond_opened_past_its_lock_by_the_shell_is_named(tmp_path, capsys):
    root = _project(tmp_path)
    _pre(root, "ls")
    active = root / ".claude" / "diamonds" / "active.yml"
    active.write_text("active_diamonds:\n  - id: l1-x\n    scale: L1\n    phase: discover\n")
    _age(active, 5)
    out = json.loads(_post(root, capsys))
    assert "l1-x (L1) cannot open yet" in out["reason"]


def test_nothing_changed_or_no_stamp_is_silent(tmp_path, capsys):
    root = _project(tmp_path)
    assert _post(root, capsys) == ""  # pre never ran: no stamp
    _pre(root, "ls")
    assert _post(root, capsys) == ""  # nothing changed since the stamp


def test_main_reads_the_hook_payload(tmp_path, monkeypatch, capsys):
    root = _project(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"tool_input": {"command": "echo x > .claude/diamonds/active.yml"}})))
    assert bsg.main(["pre"]) == 2
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert bsg.main(["pre"]) == 0
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    assert bsg.main(["other"]) == 0


def test_the_guard_is_registered_before_and_after_shell_commands():
    for name in ("hooks.json", "hooks.codex.json", "hooks.cursor.json"):
        text = (PLUGIN / "hooks" / name).read_text()
        assert "bash-state-guard.sh pre" in text and "bash-state-guard.sh post" in text, name
