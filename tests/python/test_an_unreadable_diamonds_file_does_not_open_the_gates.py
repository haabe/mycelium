"""A diamonds file that cannot be read does not open the gates (v0.322.5).

WHAT WAS WRONG. `.claude/diamonds/active.yml` says what may be built. The build gate decided
whether discovery was engaged from that file, read behind handlers that caught `ValueError`, and a
YAML error is not one: a file that did not parse crashed the check, the crash read as "not
engaged", and an edit of product code went through with nothing said. The wrong shape and an
emptied file reached the same answer by another road. Replayed 2026-10-12 on 0.322.4 in the run10
fixture (diamonds, no written purpose): refused while the file was readable, allowed once it held
git conflict markers, was invalid YAML, was a list, or was empty. A merge conflict is enough.
Prompted by an unsolicited email that named one line (`_hook_input.py:530`); the line is real and
the email's own description of it (a hidden "connection drop") is not: the file has no network
code.

Found on the way: `vercel --prod`, which the release checker lists, never reached the checker,
because the hook's cheap word filter had no word in it.

WHAT HOLDS NOW. A gate that cannot read the diamonds file refuses and says why. `purpose.yml`
that does not parse no longer crashes the check either.

The diamonds file's path is built from parts so that this file's own text is not a write to it.
"""

from __future__ import annotations

import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"
FIXTURE = ROOT / "tests" / "fixtures" / "run10"
sys.path.insert(0, str(PLUGIN / "scripts"))
import _hook_input as hi  # noqa: E402

ACTIVE = Path(".claude") / "diamonds" / ("active" + ".yml")
RULINGS = Path(".claude") / "state" / "diamond-rulings.json"
PRODUCT = "app/cadence/sms.py"
PURPOSE = "why: >-\n  Builders who start coding before they know who it is for find out first.\n"
SAYS_UNREADABLE = "cannot be read"

UNREADABLE = {
    "conflict markers": None,  # built from the fixture's own text, below
    "invalid yaml": "active_diamonds: [\n  - id: {{{ broken\n",
    "a list at the top": "- just\n- a list\n",
    "active_diamonds not a list": "active_diamonds: yes please\n",
}


def _break(project: Path, how: str) -> None:
    target = project / ACTIVE
    if how == "conflict markers":
        good = target.read_text()
        half = len(good) // 2
        target.write_text(good[:half] + "\n<<<<<<< HEAD\n" + good[half:] + "\n=======\n"
                          + good[half:] + "\n>>>>>>> theirs\n")
    else:
        target.write_text(UNREADABLE[how])


@pytest.fixture
def run10(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def _hook(name: str, project: Path, payload: dict) -> tuple[int, str, str]:
    env = {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
           "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
           "PYTHONUSERBASE": site.getuserbase(), "MYCELIUM_TODAY": "2026-09-25"}
    done = subprocess.run(["bash", str(HOOKS / name)], input=json.dumps({**payload, "cwd": str(project)}),
                          text=True, capture_output=True, env=env, cwd=project, timeout=120,
                          check=False)
    return done.returncode, done.stdout, done.stderr


def _edit(project: Path) -> dict:
    return {"tool_name": "Edit", "tool_input": {
        "file_path": str(project / PRODUCT), "old_string": "raise NotImplementedError",
        "new_string": "return None"}}


def _shell(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _with_purpose(project: Path) -> None:
    (project / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (project / ".claude" / "canvas" / "purpose.yml").write_text(PURPOSE)


# ---------------------------------------------------------------- the build gate


def test_control_with_the_file_readable_the_edit_is_refused_for_the_usual_reason(run10):
    code, _, err = _hook("discovery-gate.sh", run10, _edit(run10))
    assert code == 2 and "no delivery cycle is ready" in err and SAYS_UNREADABLE not in err


@pytest.mark.parametrize("how", sorted(UNREADABLE))
def test_an_edit_is_refused_when_the_file_cannot_be_read(run10, how):
    """RED BEFORE 0.322.5: exit 0 and silence, in this project with diamonds and no purpose."""
    _break(run10, how)
    code, _, err = _hook("discovery-gate.sh", run10, _edit(run10))
    assert code == 2, how
    assert SAYS_UNREADABLE in err and "active.yml" in err


@pytest.mark.parametrize("how", sorted(UNREADABLE))
def test_with_a_purpose_written_the_refusal_gives_the_real_reason(run10, how):
    """Before 0.322.5 this case was refused too, with the message for a missing delivery cycle."""
    _with_purpose(run10)
    _break(run10, how)
    code, _, err = _hook("discovery-gate.sh", run10, _edit(run10))
    assert code == 2 and SAYS_UNREADABLE in err


def test_an_emptied_file_is_refused_where_myceliums_record_shows_diamonds(run10):
    """RED BEFORE 0.322.5. The fixture carries `diamond-rulings.json` from the recorded run."""
    assert json.loads((run10 / RULINGS).read_text()), "the fixture's record must name a diamond"
    (run10 / ACTIVE).write_text("")
    code, _, err = _hook("discovery-gate.sh", run10, _edit(run10))
    assert code == 2 and "empty" in err


def test_control_an_empty_file_with_no_such_record_is_a_fresh_project(run10):
    """Nothing says this project ever had diamonds, so the brownfield gate's case stands."""
    (run10 / RULINGS).unlink()
    (run10 / ACTIVE).write_text("")
    assert _hook("discovery-gate.sh", run10, _edit(run10))[0] == 0


def test_control_a_project_that_never_started_is_untouched(tmp_path):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ACTIVE).write_text("active_diamonds: []\n")
    (tmp_path / "app.py").write_text("x = 1\n")
    edit = {"tool_name": "Edit", "tool_input": {"file_path": str(tmp_path / "app.py"),
                                                 "old_string": "1", "new_string": "2"}}
    assert _hook("discovery-gate.sh", tmp_path, edit)[0] == 0


def test_control_prose_is_still_free_while_the_file_is_unreadable(run10):
    _break(run10, "invalid yaml")
    (run10 / "README.md").write_text("# notes\n")
    write = {"tool_name": "Write", "tool_input": {"file_path": str(run10 / "README.md"),
                                                   "content": "# notes\nmore\n"}}
    assert _hook("discovery-gate.sh", run10, write)[0] == 0


def test_a_purpose_file_that_does_not_parse_no_longer_crashes_the_check(run10):
    """RED BEFORE 0.322.5: the YAML error escaped, the check exited 1, and that read as "not
    engaged" although the diamonds file was fine."""
    (run10 / ".claude" / "canvas").mkdir(parents=True, exist_ok=True)
    (run10 / ".claude" / "canvas" / "purpose.yml").write_text("why: [unclosed\n  - {{{\n")
    assert hi.discovery_state_code(str(run10)) == 0
    assert _hook("discovery-gate.sh", run10, _edit(run10))[0] == 2


# ---------------------------------------------------------------- beside the build gate


def test_the_brownfield_gate_leaves_the_refusal_to_the_build_gate(run10):
    """One refusal with the real reason, not a second question about existing code."""
    _break(run10, "invalid yaml")
    code, out, err = _hook("brownfield-gate.sh", run10, _edit(run10))
    assert (code, out.strip(), err.strip()) == (0, "", "")


def test_the_agent_is_told_at_the_prompt(run10):
    _break(run10, "conflict markers")
    _, out, _ = _hook("preflight.sh", run10, {"prompt": "carry on with the feature"})
    assert "DIAMONDS FILE UNREADABLE" in out and "DISCOVERY STATE: none" not in out


# ---------------------------------------------------------------- the release gate


#: The words the hook's cheap filter looks for, in the WHOLE hook input, the project's path
#: included. A test whose own temp folder is named after one of them proves nothing: the first
#: version of the test below was called "...production_deploy..." and passed on the old code.
_FILTER_WORDS = ("deploy", "publish", "push", "apply", "helm", "rollout", "image", "ssh", "scp",
                 "rsync", "upload", "pulumi", "sync", "function-code", "ngrok", "cloudflared",
                 "localtunnel", "tailscale", "railway", "gh-pages", "surge", "s3", "vercel")


@pytest.mark.parametrize("command", ["vercel --prod", "vercel --prod --yes", "npx vercel --prod"])
def test_one_hosts_live_release_reaches_the_checker(run10, command):
    """RED BEFORE 0.322.5: the hook's word filter exited before the checker that lists it."""
    here = str(run10).lower()
    assert not [w for w in _FILTER_WORDS if w in here], "the temp path would pass the filter"
    assert _hook("exposure-gate.sh", run10, _shell(command))[0] == 2


@pytest.mark.parametrize("command", [
    "fly " + "deploy", "netlify " + "deploy --prod", "railway up", "pulumi up",
    "helm install api ./chart", "kubectl set image deploy/api api=img:2", "kubectl apply -f k8s/",
    "terraform apply", "ngrok http 8000", "surge ./dist", "twine up" + "load dist/*",
    "gcloud run " + "deploy api", "tailscale funnel 3000", "ssh host 'systemctl restart api'",
    "docker build -t x --pu" + "sh .", "docker pu" + "sh org/app:1", "npm pub" + "lish",
    "cargo pub" + "lish", "serverless " + "deploy", "aws s3 sync ./dist s3://bucket",
    "aws lambda update-function-code --function-name f", "scp app.tar host:/srv/",
    "rsync -a ./dist host:/var/www/", "cloudflared tunnel run", "gh-pages -d dist",
])
def test_control_every_other_kind_of_release_reaches_the_checker_too(run10, command):
    """One sample per kind the checker lists. A kind whose words the filter does not know would
    pass in silence, which is how the host above was missed."""
    assert _hook("exposure-gate.sh", run10, _shell(command))[0] == 2, command


def test_a_release_is_refused_when_the_file_was_emptied(run10):
    """RED BEFORE 0.322.5: an empty file read as "nothing to judge" and the release was allowed."""
    (run10 / ACTIVE).write_text("")
    code, _, err = _hook("exposure-gate.sh", run10, _shell("fly " + "deploy"))
    assert code == 2 and SAYS_UNREADABLE in err


# ---------------------------------------------------------------- the reasons, one by one


@pytest.mark.parametrize(("text", "expect"), [
    ("active_diamonds: []\n", ""),
    ("dogfood: false\n", ""),
    ("<<<<<<< HEAD\nactive_diamonds: []\n=======\nactive_diamonds: []\n>>>>>>> x\n", "conflict markers"),
    ("a: [\n", "not valid YAML"),
    ("- a\n", "top level"),
    ("active_diamonds: 3\n", "not a list"),
])
def test_why_the_file_cannot_be_read(tmp_path, text, expect):
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ACTIVE).write_text(text)
    why = hi.diamonds_unreadable_why(str(tmp_path))
    assert (expect in why) if expect else (why == "")


def test_no_file_is_not_an_unreadable_file(tmp_path):
    assert hi.diamonds_unreadable_why(str(tmp_path)) == ""
    assert hi.discovery_state_code(str(tmp_path)) == 1
