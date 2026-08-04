"""G-V12 coverage proof for ci_signal.py.

THE GAP IT CLOSES. The dogfood workflow was red for thirteen consecutive pushes
across 2026-08-03/04. Every run reported failure. Nothing carried that back into
the session doing the pushing, because the flow was one-way and none of the five
hook points looked outward.

Scenario-per-guardpost:
  happy — build green                              -> silence
  happy — no .github/workflows                     -> silence, no network call
  sad   — build red for HEAD                       -> report, names run + branch
  edge  — run is for a DIFFERENT sha               -> silence (not our commit)
  edge  — run still in progress                    -> silence (do not nag)
  edge  — already reported this run                -> silence (once, not per turn)
  edge  — fresh session, already-reported run      -> reports ANYWAY
  edge  — rate limit inside the window             -> silence
  edge  — fresh session ignores the rate limit     -> reports
  edge  — detached HEAD                            -> silence
  bad   — gh missing / unauthenticated / no net    -> silence, exit 0
  bad   — gh returns malformed JSON                -> silence, exit 0
"""

import json
import subprocess
import sys

import pytest

SCRIPT = "ci_signal.py"


@pytest.fixture
def mod(scripts_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_signal",
                                                  scripts_path / SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def project(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n")
    return tmp_path


def _wire(mod, monkeypatch, *, head="abc123def456", branch="main", runs=None,
          gh_fails=False, raw=None):
    """Stub the two shell-outs so no test touches git or the network."""
    def fake(args, cwd):
        if args[:2] == ["git", "rev-parse"]:
            return branch if "--abbrev-ref" in args else head
        if args[:1] == ["gh"]:
            if gh_fails:
                return None
            return raw if raw is not None else json.dumps(runs or [])
        return None
    monkeypatch.setattr(mod, "_run", fake)


def _run_of(sha, conclusion="failure", status="completed", rid=999):
    return [{"databaseId": rid, "conclusion": conclusion, "status": status,
             "headSha": sha, "name": "dogfood"}]


# ---------------------------------------------------------------- happy


def test_green_build_is_silent(mod, project, monkeypatch):
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", conclusion="success"))
    assert mod.check(project) is None


def test_a_repo_with_no_workflows_never_calls_out(mod, tmp_path, monkeypatch):
    """Cheapest bail-out first: most repos have no CI and must cost nothing."""
    called = []
    monkeypatch.setattr(mod, "_run", lambda *a, **k: called.append(a) or None)
    assert mod.check(tmp_path) is None
    assert called == [], "made a subprocess call before checking for workflows"


# ---------------------------------------------------------------- sad


def test_red_build_for_head_is_reported(mod, project, monkeypatch):
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", rid=4242))
    msg = mod.check(project)
    assert msg is not None
    assert "CI SIGNAL" in msg
    assert "4242" in msg and "main" in msg
    assert "gh run view 4242 --log-failed" in msg
    assert "abc123de" in msg          # names the sha so it is checkable


# ---------------------------------------------------------------- edge


def test_a_run_for_a_different_commit_is_not_ours(mod, project, monkeypatch):
    """Someone else's newer push failing is not this session's business, and
    reporting it would train the reader to ignore the hook."""
    _wire(mod, monkeypatch, head="aaaa1111", runs=_run_of("bbbb2222"))
    assert mod.check(project) is None


def test_an_in_progress_run_says_nothing(mod, project, monkeypatch):
    _wire(mod, monkeypatch,
          runs=_run_of("abc123def456", conclusion=None, status="in_progress"))
    assert mod.check(project) is None


@pytest.mark.parametrize("conclusion", ["success", "skipped", "cancelled",
                                        "neutral", None])
def test_non_failure_conclusions_stay_silent(mod, project, monkeypatch,
                                             conclusion):
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", conclusion=conclusion))
    assert mod.check(project) is None


def test_the_same_run_is_reported_once_not_every_turn(mod, project, monkeypatch):
    """Stop fires after every response. Nagging is how a hook gets ignored."""
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", rid=77))
    assert mod.check(project, now=1000) is not None
    assert mod.check(project, now=1000 + mod._MIN_INTERVAL_S + 1) is None


def test_a_fresh_session_hears_about_it_again(mod, project, monkeypatch):
    """A new session is a new agent with no memory of what the last one was
    told. Suppressing on a previous session's behalf reproduces the gap."""
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", rid=77))
    assert mod.check(project, now=1000) is not None
    assert mod.check(project, now=1001, fresh_session=True) is not None


def test_the_rate_limit_suppresses_inside_the_window(mod, project, monkeypatch):
    """Stop fires after every response; without this the harness makes a
    round-trip per turn. Counts gh invocations directly rather than inferring
    from the return value, because a suppressed call and a green build both
    look like None."""
    calls = []

    def stub(args, cwd):
        if args[:2] == ["git", "rev-parse"]:
            return "main" if "--abbrev-ref" in args else "abc123def456"
        if args[:1] == ["gh"]:
            calls.append(1)
            return json.dumps(_run_of("abc123def456"))
        return None
    monkeypatch.setattr(mod, "_run", stub)

    mod.check(project, now=5000)
    assert len(calls) == 1, "first check should hit the network"
    mod.check(project, now=5000 + mod._MIN_INTERVAL_S - 1)
    assert len(calls) == 1, "made a network call inside the rate-limit window"
    mod.check(project, now=5000 + mod._MIN_INTERVAL_S + 1)
    assert len(calls) == 2, "never resumed checking after the window closed"


def test_fresh_session_ignores_the_rate_limit(mod, project, monkeypatch):
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", rid=5))
    assert mod.check(project, now=9000) is not None
    _wire(mod, monkeypatch, runs=_run_of("abc123def456", rid=6))
    assert mod.check(project, now=9001, fresh_session=True) is not None


def test_detached_head_is_silent(mod, project, monkeypatch):
    _wire(mod, monkeypatch, branch="HEAD", runs=_run_of("abc123def456"))
    assert mod.check(project) is None


# ---------------------------------------------------------------- bad


def test_gh_missing_or_unauthenticated_fails_open(mod, project, monkeypatch):
    _wire(mod, monkeypatch, gh_fails=True)
    assert mod.check(project) is None


@pytest.mark.parametrize("raw", ["{not json", "null", '{"not": "a list"}', "[]"])
def test_malformed_gh_output_fails_open(mod, project, monkeypatch, raw):
    _wire(mod, monkeypatch, raw=raw)
    assert mod.check(project) is None


def test_git_unavailable_fails_open(mod, project, monkeypatch):
    monkeypatch.setattr(mod, "_run", lambda *a, **k: None)
    assert mod.check(project) is None


def test_main_never_raises_on_garbage_stdin(scripts_path):
    r = subprocess.run([sys.executable, str(scripts_path / SCRIPT)],
                       input="{not json", capture_output=True, text=True,
                       check=False)
    assert r.returncode == 0


def test_an_internal_crash_is_recorded_not_swallowed(scripts_path, tmp_path,
                                                     monkeypatch):
    """The broad catch in main() would otherwise reproduce the very failure this
    hook exists to fix: a mechanism that reports nothing and is read as healthy.
    It must still exit 0 — never break the session — while leaving a trace."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ci_crash",
                                                  scripts_path / SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(m, "check", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("boom")))
    monkeypatch.setattr(m.sys, "stdin", __import__("io").StringIO("{}"))

    assert m.main() == 0, "must never break the session"
    stamps = list(tmp_path.glob("mycelium-ci-signal-*.json"))
    assert stamps, "crash left no trace at all — silently dead"
    rec = json.loads(stamps[0].read_text())
    assert "RuntimeError: boom" in rec.get("last_error", "")
    assert rec.get("last_error_at")
