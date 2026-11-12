"""The plugin must not use `datetime.UTC`, a name Python has only from 3.11.

The hooks run their scripts and inline snippets under whatever `python3` is first on the
builder's PATH, and most of them send stderr to /dev/null. The Python that ships with macOS at
/usr/bin/python3 is 3.9. Until this test, 31 files under hooks/ and scripts/ built a timestamp
with `datetime.UTC` (or `from datetime import UTC`): under 3.9 the line raised AttributeError
(or ImportError), the fire log and the denial ledger wrote no row, and nothing said so.
`datetime.timezone.utc` is the same object on every Python the framework runs on.

ruff's UP017 asks for the opposite rewrite, because ruff.toml's target-version is py311; it is
ignored there for this reason, and this test is what keeps the name out.

The second half runs the fire-log helper and one hook-imported script under a pre-3.11
interpreter when this machine has one (a stock Mac does, at /usr/bin/python3), and skips
otherwise.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "mycelium"
HELPER = PLUGIN / "scripts" / "_hook_fire_log.sh"

# `datetime.UTC`, `_dt.UTC`, `dt.UTC`: any attribute named UTC. And the name imported bare.
_DOTTED = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.UTC\b")
_IMPORTED = re.compile(r"^\s*from\s+datetime\s+import\s+[^\n]*\bUTC\b", re.MULTILINE)
_SUFFIXES = {".py", ".sh", ".md", ".yml", ".yaml", ".toml", ".json", ".txt"}


def offenders(root: Path) -> list[str]:
    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in _SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if _DOTTED.search(line) or _IMPORTED.search(line):
                found.append(f"{path.relative_to(root)}:{n}: {line.strip()}")
    return found


def test_no_python_3_11_utc_name_in_the_plugin():
    found = offenders(PLUGIN)
    assert not found, (
        "`datetime.UTC` exists from Python 3.11 only; macOS ships 3.9 and the hooks discard "
        "stderr, so these lines fail silently there. Use `datetime.timezone.utc`:\n  "
        + "\n  ".join(found))


def test_the_scan_sees_each_form(tmp_path):
    """A control: the three spellings the plugin used are each caught, and the fixed one is not."""
    (tmp_path / "a.py").write_text("import datetime\nx = datetime.datetime.now(datetime.UTC)\n")
    (tmp_path / "b.py").write_text("import datetime as _dt\nx = _dt.datetime.now(tz=_dt.UTC)\n")
    (tmp_path / "c.sh").write_text("python3 - <<'PY'\nfrom datetime import UTC, datetime\nPY\n")
    (tmp_path / "ok.py").write_text("import datetime\nx = datetime.timezone.utc  # UTC\n")
    found = offenders(tmp_path)
    assert [f.split(":")[0] for f in found] == ["a.py", "b.py", "c.sh"]


def _old_python() -> str | None:
    """A pre-3.11 interpreter on this machine, if there is one."""
    for cand in ("/usr/bin/python3", "/usr/local/bin/python3.9", "/usr/bin/python3.9"):
        if not Path(cand).is_file():
            continue
        probe = subprocess.run([cand, "-c", "import sys; print(sys.version_info[:2] < (3, 11))"],
                               capture_output=True, text=True, check=False, timeout=30)
        if probe.returncode == 0 and probe.stdout.strip() == "True":
            return cand
    return None


OLD = _old_python()
needs_old = pytest.mark.skipif(OLD is None, reason="no Python older than 3.11 on this machine")


@needs_old
def test_fire_log_and_denial_ledger_write_a_row_under_an_old_python(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "python3").symlink_to(OLD)
    hook = tmp_path / "fake-gate.sh"
    hook.write_text(f'. "{HELPER}"\nmycelium_log_fire ".claude/state/fake-gate-fires.jsonl" '
                    '"blocked" "src/x.py"\n')
    env = {"PATH": f"{fake}:/usr/bin:/bin", "PROJECT_DIR": str(tmp_path),
           "INPUT": json.dumps({"tool_use_id": "toolu_old_python", "session_id": "s1"})}
    subprocess.run(["bash", str(hook)], env=env, check=True, timeout=60,
                   capture_output=True, stdin=subprocess.DEVNULL)
    fire = (tmp_path / ".claude/state/fake-gate-fires.jsonl").read_text().splitlines()
    assert json.loads(fire[-1])["outcome"] == "blocked"
    assert json.loads(fire[-1])["ts"].endswith("Z")
    ledger = (tmp_path / ".claude/state/denied-calls.jsonl").read_text().splitlines()
    assert json.loads(ledger[-1])["tool_use_id"] == "toolu_old_python"


@needs_old
def test_a_hook_imported_script_runs_under_an_old_python():
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import _hook_input as h; "
            "print(h._today_date().isoformat())")
    out = subprocess.run([OLD, "-I", "-c", code, str(PLUGIN / "scripts")], capture_output=True,
                         text=True, check=False, timeout=60, env={"PATH": "/usr/bin:/bin"})
    assert out.returncode == 0, out.stderr
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", out.stdout.strip())
