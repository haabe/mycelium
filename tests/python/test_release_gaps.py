"""Coverage proofs for release_gaps.py.

Per G-V12: schema and guard rules ship with tests that fail on known-bad input.

The regression these encode is concrete. On 2026-07-30, v0.66.0 through v0.66.6
landed in a single push. `auto-release.yml` read plugin.json once at the tip and
created one Release, exiting 0. Seven documented versions never shipped, the job was
green, and nothing said otherwise for five weeks.

So the tests below care about two things above all:
  - a multi-bump push must yield EVERY version, not just the tip
  - a gap must be LOUD -- absence must never come back as an empty, contented result
"""
import subprocess
import sys
import textwrap
from pathlib import Path


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import release_gaps
    return release_gaps


# ---------------------------------------------------------------- version_key

def test_version_key_orders_numerically_not_lexically(scripts_path):
    """0.9.0 < 0.10.0. Lexical sort gets this backwards, and a wrong floor
    comparison would silently exempt versions from the gap check."""
    rg = _import(scripts_path)
    assert rg.version_key("0.9.0") < rg.version_key("0.10.0")
    assert rg.version_key("0.66.6") < rg.version_key("0.67.0")
    assert rg.version_key("0.86.0") > rg.version_key("0.85.0")


def test_version_key_tolerates_malformed_versions(scripts_path):
    """A junk version must sort last, not raise -- the gap check has to survive
    a bad changelog heading rather than crash and be disabled."""
    rg = _import(scripts_path)
    assert rg.version_key("not-a-version") > rg.version_key("99.99.99")


# ------------------------------------------------------- parse_changelog

def test_parses_only_h2_version_headings(scripts_path):
    rg = _import(scripts_path)
    text = textwrap.dedent("""\
        # Changelog
        ## v0.86.0 - a title
        some prose mentioning v0.99.0 which is not a heading
        ### v0.85.0 - an h3, not a release heading
        ## v0.66.0 - another
    """)
    assert rg.parse_changelog_versions(text) == ["0.66.0", "0.86.0"]


def test_parses_empty_changelog_without_crashing(scripts_path):
    rg = _import(scripts_path)
    assert rg.parse_changelog_versions("") == []


# ------------------------------------------------------- missing_releases

def test_the_2026_07_30_regression(scripts_path):
    """The real incident: seven versions documented, only v0.67.0 released."""
    rg = _import(scripts_path)
    documented = [f"0.66.{i}" for i in range(7)] + ["0.65.0", "0.67.0"]
    released = ["0.65.0", "0.67.0"]
    assert rg.missing_releases(documented, released) == [f"0.66.{i}" for i in range(7)]


def test_no_gaps_returns_empty(scripts_path):
    rg = _import(scripts_path)
    assert rg.missing_releases(["0.85.0", "0.86.0"], ["0.86.0", "0.85.0"]) == []


def test_floor_excludes_pre_automation_history(scripts_path):
    """149 versions were bumped before release automation existed. They are history,
    not drift; including them would make the check permanently red and therefore
    permanently ignored."""
    rg = _import(scripts_path)
    documented = ["0.23.8", "0.31.0", "0.48.2", "0.66.0"]
    assert rg.missing_releases(documented, []) == ["0.66.0"]


def test_floor_boundary_is_inclusive(scripts_path):
    """The floor version itself is in scope -- v0.49.0 was released and must be
    checked, or the boundary becomes an off-by-one hiding place."""
    rg = _import(scripts_path)
    assert rg.missing_releases(["0.49.0"], []) == ["0.49.0"]
    assert rg.missing_releases(["0.48.9"], []) == []


def test_gaps_are_returned_in_ascending_order(scripts_path):
    rg = _import(scripts_path)
    got = rg.missing_releases(["0.70.0", "0.66.0", "0.68.0"], [])
    assert got == ["0.66.0", "0.68.0", "0.70.0"]


# ------------------------------------------------------- version parsing

def test_version_from_plugin_json_handles_whitespace(scripts_path):
    rg = _import(scripts_path)
    assert rg.version_from_plugin_json('{"version"  :   "1.2.3"}') == "1.2.3"
    assert rg.version_from_plugin_json("{}") is None
    assert rg.version_from_plugin_json("") is None


# ------------------------------------------------------- versions_introduced

def _git(repo, *args):
    subprocess.run(("git", "-C", str(repo), *args), check=True,
                   capture_output=True, text=True)


def _commit_version(repo, version):
    p = repo / "plugins" / "mycelium" / ".claude-plugin"
    p.mkdir(parents=True, exist_ok=True)
    (p / "plugin.json").write_text(f'{{"version": "{version}"}}\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", f"v{version}")
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False).stdout.strip()


def test_multi_bump_push_yields_every_version(tmp_path, scripts_path, monkeypatch):
    """THE REGRESSION TEST. Seven bumps in one range must produce seven entries --
    the old workflow would have seen only the last."""
    rg = _import(scripts_path)
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    before = _commit_version(repo, "0.65.0")
    shas = [_commit_version(repo, f"0.66.{i}") for i in range(7)]
    head = shas[-1]

    monkeypatch.chdir(repo)
    got = rg.versions_introduced(before, head)
    assert [g["version"] for g in got] == [f"0.66.{i}" for i in range(7)]
    # Each version anchors to the commit that FIRST set it, not to the tip.
    assert [g["commit"] for g in got] == shas
    # The baseline version was already present and is not "introduced".
    assert "0.65.0" not in [g["version"] for g in got]


def test_zeroish_before_degrades_to_head_only(tmp_path, scripts_path, monkeypatch):
    """Force-push / first push gives an all-zero `before`. That must degrade to the
    old single-version behaviour rather than raise -- the gap check is the backstop."""
    rg = _import(scripts_path)
    repo = tmp_path / "r2"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _commit_version(repo, "0.70.0")
    head = _commit_version(repo, "0.71.0")

    monkeypatch.chdir(repo)
    got = rg.versions_introduced("0" * 40, head)
    assert [g["version"] for g in got] == ["0.71.0"]


def test_unchanged_version_introduces_nothing(tmp_path, scripts_path, monkeypatch):
    """A push that touches other files must not re-release the current version."""
    rg = _import(scripts_path)
    repo = tmp_path / "r3"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    before = _commit_version(repo, "0.80.0")
    (repo / "README.md").write_text("hello")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "docs")
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False).stdout.strip()

    monkeypatch.chdir(repo)
    assert rg.versions_introduced(before, head) == []


# ------------------------------------------------------- CLI + fail-loud contract
#
# These cover main() and the gh call. The first one below is the most important test
# in the file: an unreadable release list must ABORT, never come back as "no gaps".
# A network blip reading as a clean bill of health is the precise failure this whole
# module exists to prevent, and it would be invisible in production.

def test_unreadable_release_list_aborts_rather_than_reporting_no_gaps(
    scripts_path, monkeypatch
):
    rg = _import(scripts_path)

    class Failed:
        returncode = 1
        stdout = ""
        stderr = "gh: could not connect"

    monkeypatch.setattr(rg.subprocess, "run", lambda *a, **k: Failed())
    try:
        rg._released_from_gh()
    except SystemExit as e:
        assert e.code == 2, "must exit 2, not fall through to an empty list"
    else:
        raise AssertionError("a failed gh call must raise, never return []")


def test_released_from_gh_strips_the_v_prefix(scripts_path, monkeypatch):
    rg = _import(scripts_path)

    class OK:
        returncode = 0
        stdout = '[{"tagName": "v0.86.0"}, {"tagName": "v0.85.0"}]'
        stderr = ""

    monkeypatch.setattr(rg.subprocess, "run", lambda *a, **k: OK())
    assert rg._released_from_gh() == ["0.86.0", "0.85.0"]


def test_check_exits_1_and_names_the_gaps(scripts_path, monkeypatch, tmp_path, capsys):
    rg = _import(scripts_path)
    cl = tmp_path / "changelog.md"
    cl.write_text("## v0.85.0 - a\n\n## v0.66.0 - b\n")
    monkeypatch.setattr(rg, "_released_from_gh", lambda: ["0.85.0"])
    monkeypatch.setattr(sys, "argv", ["release_gaps.py", "--check", "--changelog", str(cl)])
    assert rg.main() == 1
    out = capsys.readouterr()
    assert "v0.66.0" in out.out, "the gap must be NAMED, not just counted"


def test_check_exits_0_when_complete(scripts_path, monkeypatch, tmp_path, capsys):
    rg = _import(scripts_path)
    cl = tmp_path / "changelog.md"
    cl.write_text("## v0.85.0 - a\n")
    monkeypatch.setattr(rg, "_released_from_gh", lambda: ["0.85.0"])
    monkeypatch.setattr(sys, "argv", ["release_gaps.py", "--check", "--changelog", str(cl)])
    assert rg.main() == 0
    assert "OK:" in capsys.readouterr().out


def test_check_ignores_pre_floor_history_end_to_end(scripts_path, monkeypatch, tmp_path):
    """A changelog full of pre-automation versions must not turn the check red."""
    rg = _import(scripts_path)
    cl = tmp_path / "changelog.md"
    cl.write_text("## v0.23.8 - old\n\n## v0.31.0 - old\n\n## v0.85.0 - current\n")
    monkeypatch.setattr(rg, "_released_from_gh", lambda: ["0.85.0"])
    monkeypatch.setattr(sys, "argv", ["release_gaps.py", "--check", "--changelog", str(cl)])
    assert rg.main() == 0


def test_introduced_mode_emits_json(scripts_path, monkeypatch, capsys):
    import json as _json
    rg = _import(scripts_path)
    monkeypatch.setattr(rg, "versions_introduced",
                        lambda b, h: [{"version": "1.0.0", "commit": "abc"}])
    monkeypatch.setattr(sys, "argv", ["release_gaps.py", "--introduced", "a", "b"])
    assert rg.main() == 0
    assert _json.loads(capsys.readouterr().out) == [{"version": "1.0.0", "commit": "abc"}]


def test_no_mode_prints_help_without_failing(scripts_path, monkeypatch, capsys):
    rg = _import(scripts_path)
    monkeypatch.setattr(sys, "argv", ["release_gaps.py"])
    assert rg.main() == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_version_at_returns_none_when_no_plugin_json(scripts_path, monkeypatch):
    """Covers the fallback: a commit predating both manifest paths yields None
    rather than an exception, so the range walk skips it instead of dying."""
    rg = _import(scripts_path)
    monkeypatch.setattr(rg, "_git", lambda *a: "")
    assert rg._version_at("deadbeef") is None
