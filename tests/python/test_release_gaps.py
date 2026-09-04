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


# ---------------------------------- squashed multi-version commits (2026-08-05)


def _commit_versions(repo, plugin_version, changelog_versions, msg=None):
    """One commit setting plugin.json AND a changelog documenting several versions.
    This is the shape a squash merge produces: N sections, one plugin.json value."""
    p = repo / "plugins" / "mycelium" / ".claude-plugin"
    p.mkdir(parents=True, exist_ok=True)
    (p / "plugin.json").write_text(f'{{"version": "{plugin_version}"}}\n')
    d = repo / "docs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "changelog.md").write_text(
        "# Changelog\n\n"
        + "\n\n".join(f"## v{v} - section\n\nbody for {v}." for v in changelog_versions)
        + "\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg or f"v{plugin_version}")
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False).stdout.strip()


def _repo(tmp_path, name):
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    return repo


def test_squashed_two_version_commit_yields_both(tmp_path, scripts_path, monkeypatch):
    """THE 2026-08-05 REGRESSION. v0.95.0 and v0.95.1 were squashed into ONE commit.
    plugin.json holds exactly one version, so the commit-walk saw only 0.95.1 and
    v0.95.0 shipped with no Release while its changelog section promised one.

    Same defect as the 2026-07-30 seven-version incident, one layer in: that was
    many versions across many COMMITS, this is many versions inside ONE. Walking the
    range cannot see it; only the changelog can, because the changelog is the claim
    of record.
    """
    rg = _import(scripts_path)
    repo = _repo(tmp_path, "squash")
    before = _commit_versions(repo, "0.94.0", ["0.94.0"])
    head = _commit_versions(repo, "0.95.1", ["0.94.0", "0.95.0", "0.95.1"])

    monkeypatch.chdir(repo)
    got = rg.versions_introduced(before, head)
    assert [g["version"] for g in got] == ["0.95.0", "0.95.1"]
    # Both anchor to the squash commit, because that is genuinely where both landed.
    assert {g["commit"] for g in got} == {head}


def test_changelog_only_version_is_still_released(tmp_path, scripts_path, monkeypatch):
    """A version documented but never written to plugin.json at all. The changelog
    promises it to consumers, so it gets a Release."""
    rg = _import(scripts_path)
    repo = _repo(tmp_path, "cl-only")
    before = _commit_versions(repo, "0.80.0", ["0.80.0"])
    head = _commit_versions(repo, "0.80.0", ["0.80.0", "0.81.0"])

    monkeypatch.chdir(repo)
    assert [g["version"] for g in rg.versions_introduced(before, head)] == ["0.81.0"]


def test_changelog_pass_respects_the_floor(tmp_path, scripts_path, monkeypatch):
    """LOAD-BEARING on a shallow or rewritten history. If `before` has no readable
    changelog, every documented version looks fresh — without the floor the step
    would try to create a Release for the entire back catalogue."""
    rg = _import(scripts_path)
    repo = _repo(tmp_path, "floor")
    before = _commit_versions(repo, "0.94.0", ["0.94.0"])
    head = _commit_versions(repo, "0.95.0", ["0.10.0", "0.48.9", "0.94.0", "0.95.0"])

    monkeypatch.chdir(repo)
    got = [g["version"] for g in rg.versions_introduced(before, head)]
    assert got == ["0.95.0"]          # 0.10.0 and 0.48.9 are below DEFAULT_FLOOR
    assert "0.48.9" not in got


def test_no_changelog_does_not_break_the_commit_walk(tmp_path, scripts_path, monkeypatch):
    """A repo with no docs/changelog.md must still release from plugin.json. The
    changelog pass degrades to empty rather than failing the release step."""
    rg = _import(scripts_path)
    repo = _repo(tmp_path, "nocl")
    before = _commit_version(repo, "0.90.0")
    head = _commit_version(repo, "0.91.0")

    monkeypatch.chdir(repo)
    assert [g["version"] for g in rg.versions_introduced(before, head)] == ["0.91.0"]


def test_results_are_version_ordered(tmp_path, scripts_path, monkeypatch):
    """Numeric order, not lexical and not commit order — 0.9.0 before 0.10.0."""
    rg = _import(scripts_path)
    repo = _repo(tmp_path, "order")
    before = _commit_versions(repo, "0.94.0", ["0.94.0"])
    head = _commit_versions(repo, "0.94.0", ["0.94.0", "0.100.0", "0.95.0", "0.96.0"])

    monkeypatch.chdir(repo)
    got = [g["version"] for g in rg.versions_introduced(before, head)]
    assert got == ["0.95.0", "0.96.0", "0.100.0"]


# ------------------------------------------------- first_commit_for_versions / --repair

def test_repair_finds_versions_a_dispatch_range_cannot_see(
    tmp_path, scripts_path, monkeypatch
):
    """THE 2026-08-07 REGRESSION TEST.

    A GitHub outage left two already-landed versions unreleased. The advertised
    repair path (workflow_dispatch) passes an empty `before`, so `versions_introduced`
    degrades to HEAD-only and offers the tip version -- which already has a Release.
    Repair must search history for what is MISSING instead.
    """
    rg = _import(scripts_path)
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    sha_100 = _commit_version(repo, "0.100.0")
    sha_101 = _commit_version(repo, "0.101.0")
    _commit_version(repo, "0.101.1")
    monkeypatch.chdir(repo)

    # NEGATIVE CONTROL: the old path, on a dispatch-shaped call, sees only the tip.
    # If this ever returns the missing versions, --repair is redundant and this whole
    # change should be reverted rather than kept as decoration.
    introduced = rg.versions_introduced("", "HEAD")
    assert [g["version"] for g in introduced] == ["0.101.1"]

    # The repair path locates both gaps, each anchored to the commit that set it.
    found = rg.first_commit_for_versions({"0.100.0", "0.101.0"})
    assert found == {"0.100.0": sha_100, "0.101.0": sha_101}


def test_repair_anchors_a_squashed_version_via_the_changelog(
    tmp_path, scripts_path, monkeypatch
):
    """A version squashed away never appears in any commit's plugin.json (the
    2026-08-05 v0.95.0 case). It must still be locatable, via the changelog."""
    rg = _import(scripts_path)
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _commit_version(repo, "0.94.0")
    # One commit carries BOTH versions in the changelog; plugin.json shows only 0.95.1.
    docs = repo / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "changelog.md").write_text("## v0.95.0 - a\n\n## v0.95.1 - b\n")
    p = repo / "plugins" / "mycelium" / ".claude-plugin"
    (p / "plugin.json").write_text('{"version": "0.95.1"}\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "squashed")
    squashed = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=False).stdout.strip()
    monkeypatch.chdir(repo)

    found = rg.first_commit_for_versions({"0.95.0"})
    assert found == {"0.95.0": squashed}


def test_repair_reports_a_version_it_cannot_locate_rather_than_dropping_it(
    tmp_path, scripts_path, monkeypatch
):
    """The fail-open this module exists to close, in its newest shape: a repair that
    silently emits a shorter list than the gap it was asked to fix."""
    rg = _import(scripts_path)
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _commit_version(repo, "0.100.0")
    monkeypatch.chdir(repo)

    found = rg.first_commit_for_versions({"0.100.0", "0.199.0"})
    assert "0.100.0" in found
    assert "0.199.0" not in found  # caller must report it, never silently skip


def test_repair_with_no_gaps_returns_empty_rather_than_everything(
    tmp_path, scripts_path, monkeypatch
):
    """Empty input honesty: nothing missing must mean nothing emitted -- not a walk
    of all history offering every version ever bumped."""
    rg = _import(scripts_path)
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    _commit_version(repo, "0.100.0")
    monkeypatch.chdir(repo)

    assert rg.first_commit_for_versions(set()) == {}


# ---------------------------------------------------------------------------
# THE MIRROR DIRECTION, added 2026-09-04.
#
# Everything above proves a documented version cannot silently fail to release.
# Nothing proved the opposite, and the opposite happened twice: v0.176.0, a phantom
# from an intermediate commit's plugin.json, and v0.107.1, a real release whose
# changelog section was never written and which went unnoticed for 27 days.
# ---------------------------------------------------------------------------


def test_undocumented_releases_finds_a_release_with_no_changelog_section(scripts_path):
    """The v0.107.1 shape: a Release exists, the changelog never described it."""
    rg = _import(scripts_path)
    assert rg.undocumented_releases(
        ["0.107.0", "0.107.1"], ["0.107.0"], floor="0.49.0"
    ) == ["0.107.1"]


def test_undocumented_releases_respects_the_floor(scripts_path):
    """Pre-automation history is history, not drift -- 149 versions predate releases
    entirely and must not be reported as strays."""
    rg = _import(scripts_path)
    assert rg.undocumented_releases(["0.20.0"], [], floor="0.49.0") == []


def test_undocumented_releases_is_empty_when_everything_is_documented(scripts_path):
    """Empty-input honesty, same contract the forward check carries: clean must come
    back clean, never as 'nothing checked'."""
    rg = _import(scripts_path)
    assert rg.undocumented_releases(["0.90.0"], ["0.90.0", "0.91.0"], floor="0.49.0") == []


def test_undocumented_releases_is_the_exact_inverse_of_missing_releases(scripts_path):
    """The two directions must not overlap or leave a hole between them: a version is
    a gap, a stray, or fine -- never two of those."""
    rg = _import(scripts_path)
    documented = ["0.90.0", "0.91.0"]
    released = ["0.90.0", "0.92.0"]
    gaps = rg.missing_releases(documented, released, floor="0.49.0")
    strays = rg.undocumented_releases(released, documented, floor="0.49.0")
    assert gaps == ["0.91.0"]
    assert strays == ["0.92.0"]
    assert not set(gaps) & set(strays)


def test_partition_withholds_the_phantom_and_keeps_the_documented(scripts_path):
    """The v0.176.0 shape: an intermediate commit carried a version that was never
    meant to ship. It must be withheld; the real one must still go out."""
    rg = _import(scripts_path)
    introduced = [
        {"version": "0.175.2", "commit": "aaa"},
        {"version": "0.176.0", "commit": "bbb"},
    ]
    releasable, withheld = rg.partition_undocumented(introduced, ["0.175.2"])
    assert [i["version"] for i in releasable] == ["0.175.2"]
    assert [i["version"] for i in withheld] == ["0.176.0"]


def test_partition_preserves_the_commit_anchor(scripts_path):
    """A withheld or kept version must keep the commit it was anchored to. Losing the
    anchor would make the later repair path tag the wrong commit -- a quiet lie the
    module already refuses elsewhere."""
    rg = _import(scripts_path)
    introduced = [{"version": "0.175.2", "commit": "deadbeef"}]
    releasable, withheld = rg.partition_undocumented(introduced, ["0.175.2"])
    assert releasable[0]["commit"] == "deadbeef"
    assert withheld == []


def test_partition_withholds_everything_when_the_changelog_is_empty(scripts_path):
    """Fail CLOSED on absent input. An unreadable or empty changelog must not read as
    'nothing to check, release it all' -- that is the fail-open this module exists to
    close, arriving from the release side instead of the detection side."""
    rg = _import(scripts_path)
    introduced = [{"version": "0.1.0", "commit": "a"}, {"version": "0.2.0", "commit": "b"}]
    releasable, withheld = rg.partition_undocumented(introduced, [])
    assert releasable == []
    assert len(withheld) == 2


# ---------------------------------------------------------------------------
# DUPLICATE CHANGELOG HEADINGS, added 2026-09-04.
#
# Every reader goes through parse_changelog_versions, which returns a SET -- so a
# version documented twice was indistinguishable from one documented once, in every
# count and every gap check. v0.108.0 carried two unrelated sections under one number
# from 2026-08-08 until someone counted headings by hand.
# ---------------------------------------------------------------------------


def test_duplicate_changelog_versions_finds_a_doubled_heading(scripts_path):
    rg = _import(scripts_path)
    text = "## v0.108.0 - one\nbody\n## v0.108.0 - two\nbody\n## v0.109.0 - three\n"
    assert rg.duplicate_changelog_versions(text) == ["0.108.0"]


def test_a_clean_changelog_has_no_duplicates(scripts_path):
    """Empty-input honesty: clean must come back clean."""
    rg = _import(scripts_path)
    assert rg.duplicate_changelog_versions("## v0.1.0 - a\n## v0.2.0 - b\n") == []


def test_duplicate_detection_respects_the_floor(scripts_path):
    """Pre-automation duplicates are reported by the caller, not blocked here."""
    rg = _import(scripts_path)
    text = "## v0.26.1 - a\n## v0.26.1 - b\n## v0.90.0 - c\n## v0.90.0 - d\n"
    assert rg.duplicate_changelog_versions(text, floor="0.49.0") == ["0.90.0"]
    assert rg.duplicate_changelog_versions(text) == ["0.26.1", "0.90.0"]


def test_parse_changelog_versions_cannot_see_what_this_check_catches(scripts_path):
    """The reason this function had to exist: the set-based reader is blind to it.
    If this ever fails, the duplicate check has become redundant -- delete it."""
    rg = _import(scripts_path)
    text = "## v0.108.0 - one\n## v0.108.0 - two\n"
    assert rg.parse_changelog_versions(text) == ["0.108.0"]
    assert rg.duplicate_changelog_versions(text) == ["0.108.0"]
