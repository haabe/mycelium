"""_hook_input.py: the shared reading every blocking hook uses (0.196.0, adversarial pass
2026-09-11). Each test is one move the reviewer used to get past a hook."""

import io
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"


def _m():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import _hook_input
    return _hook_input


# --- input shape ---------------------------------------------------------------

def test_non_string_path_is_bad_input_not_a_crash():
    m = _m()
    with pytest.raises(m.BadInputError):
        m.target_paths({"file_path": ["a"]})
    with pytest.raises(m.BadInputError):
        m.written_content({"content": ["x"]})
    with pytest.raises(m.BadInputError):
        m.written_content({"edits": "no"})


def test_every_path_key_is_read():
    m = _m()
    keys = {k for k, _ in m.target_paths({"file": "a", "path": "b", "notebook_path": "c",
                                            "source": "d", "destination": "e"})}
    assert keys == {"file", "path", "notebook_path", "source", "destination"}


def test_multiedit_edits_are_part_of_the_content():
    m = _m()
    out = m.written_content({"edits": [{"old_string": "x", "new_string": "SECRET1"},
                                       {"newText": "SECRET2"}]})
    assert "SECRET1" in out and "SECRET2" in out


# --- paths ---------------------------------------------------------------------

def test_dotdot_and_symlink_resolve_to_the_real_place(tmp_path):
    m = _m()
    (tmp_path / "src" / "xyz").mkdir(parents=True)
    (tmp_path / "src" / "other").mkdir()
    r = m.resolve("src/xyz/../other/a.py", str(tmp_path))
    assert r.rel == "src/other/a.py" and r.inside
    os.symlink(tmp_path / "src" / "other", tmp_path / "src" / "xyz" / "link")
    r = m.resolve("src/xyz/link/a.py", str(tmp_path))
    assert r.rel == "src/other/a.py"


def test_a_symlink_pointing_out_of_the_project_is_outside(tmp_path):
    m = _m()
    outside = tmp_path.parent / (tmp_path.name + "_out")
    outside.mkdir()
    os.symlink(outside, tmp_path / "out")
    r = m.resolve("out/a.py", str(tmp_path))
    assert not r.inside and r.rel is None


def test_zero_byte_file_reports_size_zero(tmp_path):
    m = _m()
    (tmp_path / "new.py").write_text("")
    r = m.resolve("new.py", str(tmp_path))
    assert r.exists and r.size == 0


def test_guard_state_is_recognised_by_real_path(tmp_path):
    m = _m()
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    r = m.resolve(".claude/state/../state/upstream.json", str(tmp_path))
    assert m.is_guard_state(r.rel) == ".claude/state/upstream.json"
    assert m.is_guard_state("src/a.py") is None


# --- bash ----------------------------------------------------------------------

@pytest.mark.parametrize("cmd", [
    "echo x > CLAUDE.md",
    "echo x > ./CLAUDE.md",
    "echo x > $PWD/CLAUDE.md",
    "echo x > ${PWD}/CLAUDE.md",
    "git status\necho x > CLAUDE.md",
    "cat > CLAUDE.md <<EOF\nhi\nEOF",
    "echo x | tee CLAUDE.md",
    "sed -i '' 's/a/b/' CLAUDE.md",
    "perl -pi -e s/a/b/ CLAUDE.md",
    "echo x | dd of=CLAUDE.md",
    "ed -s CLAUDE.md",
    "gawk -i inplace '{print}' CLAUDE.md",
    "rsync /tmp/x CLAUDE.md",
    "cp /tmp/x CLAUDE.md",
    "python3 -c \"open('CLAUDE.md','w').write('x')\"",
    "rm CLAUDE.md",
])
def test_bash_writers_name_their_target(tmp_path, cmd):
    m = _m()
    scan = m.bash_write_targets(cmd, str(tmp_path))
    assert any(t.rel == "CLAUDE.md" for t in scan.targets), (cmd, scan)


def test_bash_absolute_path_and_cd_are_followed(tmp_path):
    m = _m()
    (tmp_path / ".claude" / "engine").mkdir(parents=True)
    scan = m.bash_write_targets(f"echo x > {tmp_path}/CLAUDE.md", str(tmp_path))
    assert [t.rel for t in scan.targets] == ["CLAUDE.md"]
    scan = m.bash_write_targets("cd .claude/engine && echo x > foo.md", str(tmp_path))
    assert [t.rel for t in scan.targets] == [".claude/engine/foo.md"]


def test_bash_variable_targets_are_opaque_not_ignored(tmp_path):
    m = _m()
    scan = m.bash_write_targets("f=CLAUDE.md; echo x > $f", str(tmp_path))
    assert scan.opaque and not scan.targets


def test_bash_reads_are_not_writes(tmp_path):
    m = _m()
    scan = m.bash_write_targets("cat CLAUDE.md | grep x; git status", str(tmp_path))
    assert scan.targets == [] and scan.opaque == []


# --- decisions -----------------------------------------------------------------

def test_fail_closed_turns_a_crash_into_a_deny(capsys):
    m = _m()

    @m.fail_closed("thing")
    def boom():
        raise TypeError("nope")

    with pytest.raises(SystemExit):
        boom()
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "TypeError" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_guard_state_write_asks_the_human(tmp_path, capsys, monkeypatch):
    m = _m()
    monkeypatch.delenv("MYCELIUM_GUARD_STATE_EDIT", raising=False)
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    with pytest.raises(SystemExit):
        m.guard_state_check("gate", "Write",
                            {"file_path": str(tmp_path / ".claude/state/upstream.json")},
                            str(tmp_path))
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"
    with pytest.raises(SystemExit):
        m.guard_state_check("gate", "Bash",
                            {"command": "echo '{\"active\":false}' > .claude/state/upstream.json"},
                            str(tmp_path))
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "ask"
    monkeypatch.setenv("MYCELIUM_GUARD_STATE_EDIT", "1")
    m.guard_state_check("gate", "Write",
                        {"file_path": str(tmp_path / ".claude/state/upstream.json")}, str(tmp_path))


def test_cli_prints_targets_then_content(tmp_path, monkeypatch, capsys):
    m = _m()
    payload = {"tool_name": "MultiEdit", "tool_input": {"file_path": str(tmp_path / "a.py"),
               "edits": [{"old_string": "x", "new_string": "AKIAABCDEFGHIJKLMNOP"}]}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "argv", ["_hook_input.py", "--project-dir", str(tmp_path)])
    assert m.cli() == 0
    out = capsys.readouterr().out.split("\n")
    assert out[0] == "MultiEdit" and out[1].startswith("a.py\t0\t0")
    assert "AKIAABCDEFGHIJKLMNOP" in "\n".join(out)


# --- discovery state -------------------------------------------------------

def test_discovery_state_needs_a_real_purpose_or_an_active_diamond(tmp_path):
    m = _m()
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    diamonds = tmp_path / ".claude" / "diamonds"
    diamonds.mkdir()
    assert not m.has_discovery_state(str(tmp_path))
    (canvas / "purpose.yml").write_text(" " * 61)
    assert not m.has_discovery_state(str(tmp_path)), "sixty-one spaces are not a purpose"
    (diamonds / "active.yml").write_text("- id: fake\n")
    assert not m.has_discovery_state(str(tmp_path)), "a bare list is not an active diamond"
    (canvas / "purpose.yml").write_text('purpose:\n  statement: "Hikers decide with real trail conditions"\n')
    assert m.has_discovery_state(str(tmp_path))
    (canvas / "purpose.yml").write_text("why: |\n  We help maintainers see what the code cannot say.\n")
    assert m.has_discovery_state(str(tmp_path))
    (canvas / "purpose.yml").write_text("# nothing\n")
    (diamonds / "active.yml").write_text("active_diamonds:\n- id: l0\n  scale: L0\n")
    assert m.has_discovery_state(str(tmp_path))


def test_cli_discovery_state_flag(tmp_path, monkeypatch, capsys):
    m = _m()
    monkeypatch.setattr(sys, "argv", ["_hook_input.py", "--project-dir", str(tmp_path), "--discovery-state"])
    assert m.cli() == 1
