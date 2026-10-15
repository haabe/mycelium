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

import pytest

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
                PY_WRITE):  # a literal path in a one-liner is read as its target
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


def test_a_diamond_opened_past_its_lock_by_the_shell_is_put_back_and_named(tmp_path, capsys):
    """Since 0.325.0 the change is put back; what the locks would have said is still told."""
    root = _project(tmp_path)
    _pre(root, "ls")
    active = root / ".claude" / "diamonds" / "active.yml"
    active.write_text("active_diamonds:\n  - id: l1-x\n    scale: L1\n    phase: discover\n")
    _age(active, 5)
    out = json.loads(_post(root, capsys))
    assert "l1-x (L1) cannot open yet" in out["reason"]
    assert active.read_text() == "active_diamonds: []\n"


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
        text = (PLUGIN / "hooks" / name).read_text().replace('\\"', "")  # commands quote their paths
        assert "bash-state-guard.sh pre" in text and "bash-state-guard.sh post" in text, name


# ---------------------------------------------------------------- v0.318.1: reads are not refused

_F = ".claude/diamonds/active.yml"


@pytest.mark.parametrize("cmd", [
    f"grep -n ht-130 {_F} > $TMPDIR/hits.txt",
    f"grep -n ht-130 {_F}; echo done > $TMPDIR/log.txt",
    f"git diff --quiet {_F} && bash battery.sh > $TMPDIR/out.txt 2>&1",
    f"grep -n ht-130 {_F} > hits.txt",
])
def test_a_read_beside_a_variable_path_write_is_not_refused(tmp_path, cmd):
    """Dogfood 2026-10-09/10: four read-only commands refused in one session, the message saying
    "Reading the file is never refused". A last component that is a literal name other than
    active.yml cannot be the diamonds file."""
    assert bsg.writes_active(cmd, str(_project(tmp_path))) is False


@pytest.mark.parametrize("cmd", [
    f"cat new.yml > {_F}",
    f"sed -i '' 's/a/b/' {_F}",
    f"mv x.yml {_F}",
])
def test_control_a_write_whose_target_is_the_file_is_still_refused(tmp_path, cmd):
    assert bsg.writes_active(cmd, str(_project(tmp_path))) is True


# ---------------------------------------------------------------- v0.325.0: the file, not the text

@pytest.mark.parametrize("cmd", [
    f"f={_F}; cat new.yml > $f",
    f"grep x {_F} > $DIR/active.yml",
    f"grep x {_F} > $OUT",
    f"python3 -c 'p=f(\"{_F}\"); p.write_text(\"x\")'",
    "python3 newbar.py values.yml",
    # Dogfood 2026-10-14: appending to another file, the path only mentioned in the text.
    ("cat >> .claude/harness/upstream-candidates.yml <<'EOF'\n- id: x\n  surfaced_by: the agent "
     f"ran python3 newbar.py, a script that opens {_F} and writes it. The next command, `sed -i "
     f"...\n  {_F}`, was refused.\nEOF"),
])
def test_a_write_the_text_does_not_show_is_left_to_the_comparison(tmp_path, cmd):
    """Until 0.325.0 a command that named the file and wrote somewhere unseen was refused: the
    heredoc above was, while `python3 newbar.py`, which wrote the file from inside the script, was
    not. Neither is refused now; what a command actually did to the file is judged afterwards."""
    assert bsg.writes_active(cmd, str(_project(tmp_path))) is False


def test_a_script_that_names_the_file_only_inside_itself_is_put_back(tmp_path, capsys):
    """RED ON 0.324.0: the 2026-10-14 shape. A script replaced a diamond's definition of done; the
    scale locks found nothing to object to and the change stood, unsaid."""
    root = _project(tmp_path)
    active = root / _F
    was = ("active_diamonds:\n- id: l1-x\n  scale: L1\n  definition_of_done:\n    outcome: old\n"
           "- id: l2-y\n  scale: L2\n")
    active.write_text(was)
    payload = {"tool_use_id": "c1", "session_id": "s1",
               "tool_input": {"command": "python3 newbar.py values.yml"}}
    assert bsg.pre(payload, root) == 0
    active.write_text(was.replace("outcome: old", "outcome: new"))
    assert bsg.post(payload, root) == 0
    said = json.loads(capsys.readouterr().out)
    assert active.read_text() == was
    assert "(l1-x)" in said["reason"] and "you were not asked first" in said["systemMessage"]
    kept = said["reason"].split("kept at ")[1].split(". ")[0]
    assert (root / kept).read_text() == was.replace("outcome: old", "outcome: new")
    assert "Edit or Write" in said["reason"]
