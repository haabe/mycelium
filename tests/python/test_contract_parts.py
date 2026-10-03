"""scripts/contract_parts.py: the operating contract reaches the model whole (v0.310.16).

Claude Code caps a hook's additionalContext at 10,000 characters and shows only a 2,000-character
preview of anything longer. The contract is split between its sections so each part fits, and
the plugin root replaces the literal ${CLAUDE_PLUGIN_ROOT}, which is not set in Claude's shell.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "mycelium" / "scripts" / "contract_parts.py"
sys.path.insert(0, str(SCRIPT.parent))
import contract_parts as cp  # noqa: E402


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


def test_the_shipped_contract_fits_the_registered_handlers():
    r = run("--check")
    assert r.returncode == 0, r.stdout
    parts = cp.split(cp.CONTRACT.read_text(encoding="utf-8"), "/plugin/root")
    assert len(parts) <= cp.MAX_PARTS
    assert all(len(p) <= cp.PART_LIMIT < cp.CAP for p in parts)


def test_every_section_of_the_contract_arrives_once():
    text = cp.CONTRACT.read_text(encoding="utf-8")
    joined = "\n".join(cp.split(text, "/plugin/root"))
    for line in text.splitlines():
        if line.startswith("## "):
            assert joined.count(line) == 1, line


def test_the_plugin_root_replaces_the_literal_and_part_one_states_it():
    parts = cp.split("intro\n\n## A\nrun ${CLAUDE_PLUGIN_ROOT}/scripts/x.py\n", "/opt/myc")
    assert "/opt/myc/scripts/x.py" in parts[0]
    assert "the Mycelium plugin root is /opt/myc" in parts[0]
    assert "run ${CLAUDE_PLUGIN_ROOT}" not in parts[0]


def test_parts_are_numbered_so_parallel_delivery_can_be_read_as_one():
    big = "\n\n".join(f"## S{i}\n" + "x" * 3000 for i in range(5))
    parts = cp.split(big, "/r")
    assert len(parts) > 1
    for k, p in enumerate(parts, 1):
        assert p.startswith(f"MYCELIUM OPERATING CONTRACT, part {k} of {len(parts)}.")


def test_a_section_too_large_for_any_part_fails_the_check(tmp_path):
    f = tmp_path / "c.md"
    f.write_text("## Huge\n" + "x" * 12_000, encoding="utf-8")
    r = run("--check", "--contract", str(f))
    assert r.returncode == 1 and "FAIL" in r.stdout


def test_more_parts_than_handlers_fails_the_check(tmp_path):
    f = tmp_path / "c.md"
    f.write_text("\n\n".join(f"## S{i}\n" + "x" * 8_000 for i in range(cp.MAX_PARTS + 1)), encoding="utf-8")
    r = run("--check", "--contract", str(f))
    assert r.returncode == 1 and "no longer fits" in r.stdout


def test_a_part_past_the_last_emits_nothing_and_a_real_part_emits_hook_json():
    assert run("--part", "99").stdout == ""
    out = json.loads(run("--part", "1").stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert len(out["hookSpecificOutput"]["additionalContext"]) <= cp.CAP


def test_every_manifest_registers_one_handler_per_part():
    hooks = REPO / "plugins" / "mycelium" / "hooks"
    for name in ("hooks.json", "hooks.codex.json", "hooks.cursor.json"):
        text = (hooks / name).read_text(encoding="utf-8").replace('\\"', "")
        for k in range(1, cp.MAX_PARTS + 1):
            assert f"contract-part.sh {k}" in text, (name, k)


# In-process runs of main(), so coverage sees the branches the subprocess tests exercise.
def test_main_check_passes_on_the_shipped_contract(capsys):
    assert cp.main(["--check"]) == 0
    assert "part(s)" in capsys.readouterr().out


def test_main_check_fails_on_a_contract_that_does_not_fit(tmp_path, capsys):
    f = tmp_path / "c.md"
    f.write_text("\n\n".join(f"## S{i}\n" + "x" * 8_000 for i in range(cp.MAX_PARTS + 1)),
                 encoding="utf-8")
    assert cp.main(["--check", "--contract", str(f)]) == 1
    assert "no longer fits" in capsys.readouterr().out


def test_main_check_reports_a_missing_contract(tmp_path, capsys):
    assert cp.main(["--check", "--contract", str(tmp_path / "absent.md")]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_main_part_emits_json_and_a_missing_contract_emits_nothing(tmp_path, capsys):
    assert cp.main(["--part", "2"]) == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert cp.main(["--part", "1", "--contract", str(tmp_path / "absent.md")]) == 0
    assert capsys.readouterr().out == ""
    assert cp.main(["--part", "99"]) == 0
    assert capsys.readouterr().out == ""
