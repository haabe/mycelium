"""The release gate's inputs, from the 2026-10-01 control audit (DL-1370, batch 1a: P1-P5).

Each gap was reproduced on 0.307.2 before it was fixed. Every diamond here records its decisions
directly (founder rule, 2026-10-01: a control's fixture must not get the record it tests from the
shared phase conversion).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hook_input as hi  # noqa: E402
import scale_locks as sl  # noqa: E402
import test_scale_locks as tsl  # noqa: E402 - the suite's canvas ladder, nothing converted

DELIVERED = [{"decision": d, "on": "2026-09-20"}
             for d in ("set_target", "start_experiment", "commit_to_build", "release")]
CLOSED = [*DELIVERED, {"decision": "close", "on": "2026-09-24"}]


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-09-25")


def _l3(**record) -> dict:
    return {"id": "l3-a", "scale": "L3", "object_ref": "sol-001", "evidence_type": "anecdotal",
            "theory_gates_status": dict(tsl.EXPOSE_PASSED), "decisions": list(DELIVERED),
            "exposures": [{**tsl.RECORD, **record}]}


def _project(tmp_path: Path, diamonds: list[dict]) -> str:
    return tsl._project(tmp_path, purpose=tsl.PURPOSE, opps=tsl._full_opps(), diamonds=diamonds)


def _release(p: str, command: str = "fly deploy"):
    return sl._release_decision(p, command)  # the gate's own decision


# P1 -------------------------------------------------------------------------------------------

def test_a_project_whose_diamonds_have_all_completed_is_still_judged(tmp_path):
    """P1: `if not st.active: return None` read "no open diamonds" as "no diamonds at all", so a
    deploy passed once every diamond had completed (on 0.288.1 too)."""
    p = _project(tmp_path, [])
    active = Path(p) / ".claude" / "diamonds" / "active.yml"
    done = {**_l3(), "decisions": list(CLOSED)}
    active.write_text(yaml.safe_dump({"active_diamonds": [], "completed_diamonds": [done]}))
    verdict = _release(p)
    assert verdict and verdict[0] == "deny", verdict
    empty = tmp_path / "empty"
    (empty / ".claude").mkdir(parents=True)
    assert _release(str(empty)) is None, "control: a project with no diamonds at all is not judged"


# P2 -------------------------------------------------------------------------------------------

RELEASES = [
    "npx wrangler deploy", "npx wrangler pages deploy dist", "firebase deploy --only hosting",
    "railway up", "npx netlify-cli deploy --prod", "npx gh-pages -d dist",
    "npx surge ./dist myapp.surge.sh", "aws s3 cp dist s3://site --recursive",
    "supabase functions deploy notify", "docker buildx build --push -t me/app .",
    "npm run deploy", "make deploy", "./scripts/deploy.sh", "bash scripts/publish.sh",
    "pnpm run deploy:prod", "cd web && yarn deploy",
]
NOT_RELEASES = [
    "git log --grep deploy", "echo deploy", "grep -rn deploy docs/", "npm run build",
    "make test", "aws s3 cp s3://site/index.html .", "docker build -t me/app .",
    "cat scripts/deploy.sh", "vim deploy.md", "pytest tests/test_deploy.py",
]


@pytest.mark.parametrize("command", RELEASES)
def test_a_release_by_a_tool_the_gate_did_not_list_is_seen(tmp_path, command):
    """P2 (DL-1370: the list, plus a command whose subcommand or script is `deploy`/`publish`)."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    assert sl._release_in(str(tmp_path), payload), command


@pytest.mark.parametrize("command", RELEASES)
def test_each_release_is_refused_through_the_hook_itself(tmp_path, command):
    """The function seeing it is not enough: the hook skips any command its keyword pre-filter
    does not name, which is how `railway up`, `gh-pages`, `surge` and `aws s3 cp` passed the
    first version of this fix while its function test was green."""
    import json
    import os
    import subprocess
    p = _project(tmp_path, [])
    active = Path(p) / ".claude" / "diamonds" / "active.yml"
    active.write_text(yaml.safe_dump({"active_diamonds": [], "completed_diamonds": [
        {**_l3(), "decisions": list(CLOSED)}]}))
    hook = SCRIPTS.parent / "hooks" / "exposure-gate.sh"
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env.update(CLAUDE_PROJECT_DIR=p, CLAUDE_PLUGIN_ROOT=str(SCRIPTS.parent))
    r = subprocess.run(["bash", str(hook)], text=True, capture_output=True, env=env, timeout=60,
                       input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                       check=False)
    assert r.returncode == 2, (command, r.stderr[:200])


@pytest.mark.parametrize("command", NOT_RELEASES)
def test_control_a_command_that_only_names_deploy_is_not_a_release(tmp_path, command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    assert sl._release_in(str(tmp_path), payload) == "", command


# P3 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("until", ["25.10.2026", "end of October", "Oct 25 2026"])
def test_an_end_date_that_is_not_iso_does_not_keep_a_record_current(tmp_path, monkeypatch, until):
    """P3: `until` was compared as text, so a date written any other way never passed."""
    monkeypatch.setenv("MYCELIUM_TODAY", "2026-12-15")
    p = _project(tmp_path, [_l3(until=until)])
    verdict = _release(p)
    assert verdict and verdict[0] == "deny" and "YYYY-MM-DD" in verdict[1], verdict


def test_control_an_iso_end_date_in_the_future_is_current(tmp_path):
    assert _release(_project(tmp_path, [_l3(until="2026-10-25")])) is None, "one current: allowed"


def test_a_widening_to_an_end_date_that_is_not_iso_is_judged(tmp_path):
    """P3: `new < old` as text read "1 Nov 2026" as ending sooner than 2026-10-25."""
    st = sl.State(_project(tmp_path, [_l3()]))
    before = _l3(until="2026-10-25")
    after = _l3(until="1 Nov 2026")
    assert st.audience_change_missing(before, after)
    sooner = _l3(until="2026-10-20")
    assert st.audience_change_missing(before, sooner) is None, "control: an ISO date ending sooner"


# P4 -------------------------------------------------------------------------------------------

def _ack(tmp_path: Path, text: str) -> str:
    state = tmp_path / ".claude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "delivery-skip-ack").write_text(text)
    return str(tmp_path)


@pytest.mark.parametrize("text", [
    "recorded_at: 24.09.2026\ncovers: [prototypes/]\nwhy: spike\n",
    "covers: [prototypes/]\nexpires: 2026-10-01\nwhy: spike\n",
    "recorded_at: last tuesday\nreleases: true\n",
])
def test_a_structured_ack_without_an_iso_date_lifts_nothing(tmp_path, text):
    """P4: a structured ack whose `recorded_at` was missing or not ISO fell to the legacy path,
    which lifts every gate, releases included, for SKIP_ACK_LEGACY_DAYS."""
    p = _ack(tmp_path, text)
    lifted, why = hi.skip_ack_verdict(p, "release", [])
    assert not lifted and "recorded_at" in why, why
    lifted, _ = hi.skip_ack_verdict(p, "build", ["prototypes/a.py"])  # inside its `covers`
    assert not lifted


def test_control_a_bare_old_ack_keeps_its_grace_and_an_iso_ack_its_scope(tmp_path):
    bare = _ack(tmp_path / "a", "2026-07-02: user said just build it\n")
    assert hi.skip_ack_verdict(bare, "build", ["app.py"])[0]
    scoped = _ack(tmp_path / "b", "recorded_at: 2026-09-24\ncovers: [prototypes/]\n")
    assert hi.skip_ack_verdict(scoped, "build", ["prototypes/a.py"])[0]
    assert not hi.skip_ack_verdict(scoped, "release", [])[0]


# P5 -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("data_class", ["Personal data", "personal, contact details",
                                        "sensitive (health)", "PII", "names"])
def test_personal_data_however_written_asks_the_person(data_class):
    """P5: the ask (ruling g) matched the exact enum; anything other than `none` or `synthetic`
    now asks, and the record is not current until the class is one of the four."""
    before = yaml.safe_dump({"active_diamonds": [{**_l3(), "exposures": []}]})
    after = yaml.safe_dump({"active_diamonds": [_l3(data_class=data_class)]})
    assert sl.new_person_exposures(before, after)


def test_a_data_class_outside_the_four_keeps_the_record_from_being_current(tmp_path):
    verdict = _release(_project(tmp_path, [_l3(data_class="Personal data")]))
    assert verdict and verdict[0] == "deny" and "data_class" in verdict[1], verdict


@pytest.mark.parametrize("data_class", ["none", "synthetic", "Synthetic"])
def test_control_no_or_synthetic_data_asks_nobody(data_class):
    before = yaml.safe_dump({"active_diamonds": [{**_l3(), "exposures": []}]})
    after = yaml.safe_dump({"active_diamonds": [_l3(data_class=data_class)]})
    assert sl.new_person_exposures(before, after) == []
