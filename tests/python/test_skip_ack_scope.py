"""The delivery skip-ack is scoped, dated, expiring and logged (v0.293.0; founder ruling DL-1364).

Until now the mere existence of `.claude/state/delivery-skip-ack` lifted the build and release gates
for every future piece of work in the repo, forever, and the file was gitignored. Now it names the
paths it covers, lifts a release only when it says `releases: true`, lasts 30 days unless `expires`
says otherwise, and every use is logged. An old bare file is honoured for 14 days from the day this
version first sees it, with a warning at each use, then ignored.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
HOOKS = ROOT / "plugins" / "mycelium" / "hooks"
_spec = importlib.util.spec_from_file_location("_hook_input_ack", SCRIPTS / "_hook_input.py")
hi = importlib.util.module_from_spec(_spec)
sys.modules["_hook_input_ack"] = hi
_spec.loader.exec_module(hi)

ACK = ".claude/state/delivery-skip-ack"


def _project(tmp_path: Path, ack: str | None) -> Path:
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    if ack is not None:
        (tmp_path / ACK).write_text(ack)
    return tmp_path


RECORD = ("recorded_at: 2026-09-30\ncovers: [prototypes/]\nwhy: \"the founder's own words\"\n")


def test_a_scoped_ack_lifts_the_build_gate_only_for_its_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    p = _project(tmp_path, RECORD)
    assert hi.skip_ack_verdict(str(p), "build", ["prototypes/spike.py"])[0] is True
    assert hi.skip_ack_verdict(str(p), "build", ["app/cadence/sms.py"])[0] is False


def test_a_release_is_lifted_only_when_the_ack_names_releases(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    assert hi.skip_ack_verdict(str(_project(tmp_path, RECORD)), "release", [])[0] is False
    q = _project(tmp_path / "rel", RECORD + "releases: true\n")
    assert hi.skip_ack_verdict(str(q), "release", [])[0] is True


def test_it_expires_after_thirty_days_by_default(tmp_path, monkeypatch):
    p = _project(tmp_path, RECORD)
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-30")
    assert hi.skip_ack_verdict(str(p), "build", ["prototypes/a.py"])[0] is True
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-31")
    lifted, warning = hi.skip_ack_verdict(str(p), "build", ["prototypes/a.py"])
    assert lifted is False and "expired on 2026-10-30" in warning


def test_every_use_is_logged(tmp_path, monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-05")
    p = _project(tmp_path, RECORD)
    hi.skip_ack_verdict(str(p), "build", ["prototypes/a.py"])
    rows = [json.loads(x) for x in (p / hi.SKIP_ACK_USES_REL).read_text().splitlines()]
    assert rows and rows[-1]["gate"] == "build" and rows[-1]["legacy"] is False


def test_an_old_bare_ack_is_honoured_for_fourteen_days_with_a_warning(tmp_path, monkeypatch):
    p = _project(tmp_path, "the user said skip it, 2026-08-01\n")
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-01")
    lifted, warning = hi.skip_ack_verdict(str(p), "release", [])
    assert lifted is True and "honoured until 2026-10-15" in warning
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-10-16")
    lifted, warning = hi.skip_ack_verdict(str(p), "release", [])
    assert lifted is False and "grace ended on 2026-10-15" in warning


def test_control_no_ack_lifts_nothing(tmp_path):
    assert hi.skip_ack_verdict(str(_project(tmp_path, None)), "build", ["a.py"]) == (False, "")


# --- through the gates, on E2E run 10's recorded state --------------------------------------------

def _gate(name: str, project: Path, payload: dict, today: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("MYCELIUM_", "CLAUDE_"))}
    env.update({"CLAUDE_PROJECT_DIR": str(project), "MYCELIUM_TODAY": today, "PYTHONPATH": ""})
    return subprocess.run(["bash", str(HOOKS / name)], input=json.dumps(payload), text=True,
                          capture_output=True, env=env, timeout=60, check=False)


@pytest.fixture
def run10(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "tests" / "fixtures" / "run10", tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_run10_with_a_scoped_ack_builds_its_prototype_but_not_its_product(run10):
    (run10 / ACK).write_text("recorded_at: 2026-09-30\ncovers: [prototypes/]\n")
    proto = {"tool_name": "Write", "tool_input": {"file_path": str(run10 / "prototypes/spike.py"),
                                                  "content": "x = 1\n"}}
    product = {"tool_name": "Write", "tool_input": {"file_path": str(run10 / "app/cadence/web.py"),
                                                    "content": "x = 1\n"}}
    assert _gate("discovery-gate.sh", run10, proto, "2026-10-05").returncode == 0
    assert _gate("discovery-gate.sh", run10, product, "2026-10-05").returncode == 2


def test_run10_with_a_scoped_ack_still_cannot_release(run10):
    (run10 / ACK).write_text("recorded_at: 2026-09-30\ncovers: [app/]\n")
    release = {"tool_name": "Bash", "tool_input": {"command": "fly " + "deploy"}}
    assert _gate("exposure-gate.sh", run10, release, "2026-10-05").returncode == 2


def test_run10_legacy_ack_is_honoured_with_a_message_to_the_user(run10):
    (run10 / ACK).write_text("skip\n")
    release = {"tool_name": "Bash", "tool_input": {"command": "fly " + "deploy"}}
    res = _gate("exposure-gate.sh", run10, release, "2026-10-05")
    assert res.returncode == 0 and "honoured until" in json.loads(res.stdout)["systemMessage"]
