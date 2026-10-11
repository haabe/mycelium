"""Coverage tests for check_cycle_recording.py — the meta-dogfood cycle trigger.

Locks in the defect this shipped for (dogfood 2026-08-06): every trigger in
`engine/cycle-learning.md#when-to-record` was keyed to the LEAF lifecycle, and
the only opener of a `meta-dogfood` cycle in the codebase fired at a diamond
PHASE TRANSITION. Framework work does not move diamonds through phases — it
ships releases. So the dogfood project shipped 48 minor releases across 49 days
with zero cycles, and nothing could distinguish "no cycle was owed" from "a
cycle was owed and nobody noticed".

The absent-input cases carry as much weight as the positive one. This check
lives inside anti-pattern #9 (Fail-Open on Absent Input), so a branch that
cannot tell "no releases exist" from "my pattern never matched" would reproduce
the class it was built against — hence the `no-releases-matched` token test and
the loud failure when git cannot be reached at all.
"""
import subprocess
import sys

import _scratch_git


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_cycle_recording

    return check_cycle_recording


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(path, subjects=()):
    """Build a real git repo whose commit subjects are `subjects`."""
    path.mkdir(parents=True, exist_ok=True)
    _scratch_git.init(path)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "T")
    for i, subject in enumerate(subjects):
        (path / f"f{i}.txt").write_text(str(i))
        _git(path, "add", "-A")
        _git(path, "commit", "-q", "-m", subject)
    return path


def _cycles(project, *completions):
    """Write a cycle-history.yml with the given completed_at stamps."""
    body = ["schema_version: 1", "cycles:"]
    for i, stamp in enumerate(completions, start=1):
        body.append(f"  - cycle_id: cycle-{i:03d}")
        body.append("    cycle_class: meta-dogfood")
        body.append(f'    completed_at: "{stamp}"')
    if not completions:
        body[-1] = "cycles: []"
    path = project / ".claude" / "canvas" / "cycle-history.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n")
    return path


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_cycle_recording", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


# --- the positive case: releases piled up after a recorded cycle -------------

def test_arc_owed_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [
        "v0.90.0: a", "v0.91.0: b", "v0.92.0: c", "v0.93.0: d", "v0.94.0: e",
    ])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "cycle-001" in out          # names the cycle it measured from
    assert "retrospective" in out      # states the one available remedy


def test_arc_under_threshold_passes(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "OK" in capsys.readouterr().out


def test_patch_releases_do_not_count(scripts_path, tmp_path):
    """Steady-state maintenance earns no cycle — the 2026-06-18 ruling."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [
        "v0.90.1: a", "v0.90.2: b", "v0.90.3: c", "v0.90.4: d", "v0.90.5: e",
    ])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0


def test_two_releases_in_one_subject_both_counted(scripts_path, tmp_path):
    """Upstream v0.95.2 exists because an earlier step read only the first."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.95.0 + v0.96.0: two in one commit"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--threshold", "2") == 1


# --- absent-input discipline (anti-pattern #9) ------------------------------

def test_no_cycle_history_is_a_precondition_failure_not_a_pass(scripts_path, tmp_path, capsys):
    """Exit 0 would assert "I looked and everything is fine" over nothing looked at.

    This originally returned 0 as an honest skip. check_empty_input_honesty.py
    rejected it: a check reporting success over an empty population reads green
    forever. Exit 2 says "I could not assess", which is what happened.
    """
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])

    assert _run(mod, "--project-dir", str(project)) == 2
    err = capsys.readouterr().err
    assert "NOTHING WAS ASSESSED" in err
    assert "not a pass" in err


def test_never_recorded_is_its_own_state_not_a_giant_arc(scripts_path, tmp_path, capsys):
    """An unmeetable demand gets muted, which leaves the check decorative."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [f"v0.{n}.0: r" for n in range(10, 40)])
    _cycles(project)  # file exists, zero cycles

    assert _run(mod, "--project-dir", str(project)) == 1
    out = capsys.readouterr().out
    assert "never-recorded" in out
    assert "NOT an arc" in out
    assert "one-time step" in out


def test_no_releases_matched_says_so_with_its_pattern(scripts_path, tmp_path, capsys):
    """'None found' and 'my pattern is broken' must not be the same output."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: no version here", "fix: nor here"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 0
    out = capsys.readouterr().out
    assert "no-releases-matched" in out
    assert "commit subject" in out
    assert "pattern was" in out         # shows its working


def test_no_releases_matched_has_its_own_status_not_ok(scripts_path, tmp_path, capsys):
    """The STATUS field, not just the detail string, must distinguish the branches.

    The sibling test above asserts the token appears in the output — and it passed
    identically while `status` was `"ok"`, because it never read `status`. A consumer
    that reacts to named statuses (session-start.sh does) therefore saw "nothing to
    report" from a check that had correctly reported it could not measure. Observed in
    the dogfood repo 2026-08-16: two minor releases shipped upstream that day, this
    returned ok/0, and the reminder stayed silent. Assert the field consumers actually
    read, in both directions.
    """
    import json as _json
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: no version here", "fix: nor here"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--json") == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "no-releases-matched"
    assert payload["status"] != "ok"        # failure direction: the defect this fixes
    assert payload["releases"] == 0


def test_real_releases_still_report_ok_or_owed(scripts_path, tmp_path, capsys):
    """Guard the other direction: the new token must not swallow genuine measurements."""
    import json as _json
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["release: v1.2.0 ship it"])
    _cycles(project, "2000-01-01T00:00:00Z")

    _run(mod, "--project-dir", str(project), "--json")
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] in ("ok", "cycle-owed")
    assert payload["status"] != "no-releases-matched"


def test_not_a_git_repo_fails_loud_not_silent(scripts_path, tmp_path, capsys):
    """'I could not look' must never render as 'nothing to report'."""
    mod = _import(scripts_path)
    project = tmp_path / "plain"
    (project / ".claude" / "canvas").mkdir(parents=True)
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 2
    assert "ERROR" in capsys.readouterr().err


# --- cross-repo pairing -----------------------------------------------------

def test_release_repo_can_differ_from_ledger_and_is_disclosed(scripts_path, tmp_path, capsys):
    """A dogfood consumer records cycles locally while releases ship upstream.

    Scanning the wrong repo yields a plausible number rather than an error, so
    the output must always say where the count came from.
    """
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["chore: local work only"])
    upstream = _repo(tmp_path / "upstream", [f"v0.{n}.0: r" for n in range(10, 20)])
    _cycles(ledger, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(ledger), "--release-repo", str(upstream)) == 1
    out = capsys.readouterr().out
    assert "releases counted in" in out
    assert str(upstream) in out


def test_missing_release_repo_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--release-repo", str(tmp_path / "nope")) == 2
    assert "not a directory" in capsys.readouterr().err


# --- threshold resolution ---------------------------------------------------

def test_threshold_read_from_canvas(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text(
        "thresholds:\n  cycle_recording_arc:\n    default: 2\n    calibrated: null\n"
    )

    assert _run(mod, "--project-dir", str(project)) == 1
    assert "cycle_recording_arc" in capsys.readouterr().out


def test_calibrated_threshold_wins_over_default(scripts_path, tmp_path):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a", "v0.91.0: b"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text(
        "thresholds:\n  cycle_recording_arc:\n    default: 2\n    calibrated: 9\n"
    )

    assert _run(mod, "--project-dir", str(project)) == 0


def test_unreadable_thresholds_falls_back_visibly(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text("{[not: valid yaml")

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "unreadable" in capsys.readouterr().out


def test_bad_release_pattern_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--release-pattern", "((") == 2
    assert "bad --release-pattern" in capsys.readouterr().err


def test_json_output_is_machine_readable(scripts_path, tmp_path, capsys):
    import json

    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [f"v0.{n}.0: r" for n in range(10, 20)])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "cycle-owed"
    assert payload["releases"] == 10


# --- 0.310.0: what the check reads (dogfood 2026-10-02, DL-1375) -------------
# The check read "OK, 1 minor release" while about 111 had shipped. Two causes,
# either sufficient: upstream subjects dropped the `v` at 0.228.0, and nothing
# passed --release-repo for a consumer. Each test below fails on 0.309.6.

def test_unprefixed_release_subjects_are_counted(scripts_path, tmp_path):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", [f"0.{n}.0: r (#{n})" for n in range(228, 233)])
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project)) == 1


def test_an_unprefixed_version_mentioned_mid_subject_is_not_a_release(scripts_path, tmp_path, capsys):
    """'0.307.1: what 0.307.0 still read' is a patch that NAMES a minor release."""
    import json as _json
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["0.307.1: what 0.307.0 still read in the old shape"])
    _cycles(project, "2000-01-01T00:00:00Z")

    _run(mod, "--project-dir", str(project), "--json")
    assert _json.loads(capsys.readouterr().out)["status"] == "no-releases-matched"


def test_one_release_named_twice_counts_once(scripts_path, tmp_path, capsys):
    import json as _json
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.95.0: ship", "fix: the v0.95.0 regression", "v0.96.0: next"])
    _cycles(project, "2000-01-01T00:00:00Z")

    _run(mod, "--project-dir", str(project), "--json")
    payload = _json.loads(capsys.readouterr().out)
    assert payload["releases"] == 2


def _arc_config(project, body):
    path = project / ".claude" / "canvas" / "thresholds.yml"
    path.write_text("thresholds:\n  cycle_recording_arc:\n    default: 5\n" + body)


def test_release_repo_is_read_from_the_canvas_and_disclosed(scripts_path, tmp_path, capsys):
    """The hook passes --project-dir only; the canvas setting must reach it anyway."""
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["chore: local work, mentions v0.198.0"])
    upstream = _repo(tmp_path / "upstream", [f"0.{n}.0: r" for n in range(228, 238)])
    _cycles(ledger, "2000-01-01T00:00:00Z")
    _arc_config(ledger, f"    release_repo: {upstream}\n")

    assert _run(mod, "--project-dir", str(ledger)) == 1
    out = capsys.readouterr().out
    assert str(upstream) in out
    assert "thresholds.yml#cycle_recording_arc.release_repo" in out


def test_a_relative_release_repo_resolves_against_the_project(scripts_path, tmp_path):
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["chore: local work only"])
    _repo(tmp_path / "upstream", [f"v0.{n}.0: r" for n in range(10, 20)])
    _cycles(ledger, "2000-01-01T00:00:00Z")
    _arc_config(ledger, "    release_repo: ../upstream\n")

    assert _run(mod, "--project-dir", str(ledger)) == 1


def test_a_missing_configured_release_repo_is_a_status_not_silence(scripts_path, tmp_path, capsys):
    """session-start discards stderr, so 'could not look' must arrive as JSON."""
    import json as _json
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["v0.90.0: a"])
    _cycles(ledger, "2000-01-01T00:00:00Z")
    _arc_config(ledger, f"    release_repo: {tmp_path / 'not-on-this-machine'}\n")

    assert _run(mod, "--project-dir", str(ledger), "--json") == 2
    payload = _json.loads(capsys.readouterr().out)
    assert payload["status"] == "release-repo-missing"
    assert "not-on-this-machine" in payload["detail"]


def test_the_cli_release_repo_wins_over_the_canvas(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    ledger = _repo(tmp_path / "ledger", ["chore: local"])
    upstream = _repo(tmp_path / "upstream", ["v0.90.0: a"])
    _cycles(ledger, "2000-01-01T00:00:00Z")
    _arc_config(ledger, f"    release_repo: {tmp_path / 'missing'}\n")

    assert _run(mod, "--project-dir", str(ledger), "--release-repo", str(upstream)) == 0
    assert "from --release-repo" in capsys.readouterr().out


def test_a_thresholds_file_without_its_table_says_so(scripts_path, tmp_path, capsys):
    """The dogfood shape: every threshold nested under _meta after a deleted key."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.90.0: a"])
    _cycles(project, "2000-01-01T00:00:00Z")
    (project / ".claude/canvas/thresholds.yml").write_text(
        "_meta:\n  version: 1\n  cycle_recording_arc:\n    default: 2\n"
    )

    assert _run(mod, "--project-dir", str(project)) == 0
    assert "no `thresholds` table" in capsys.readouterr().out


# --- 0.319.2: the release record is the tags, when the repository has them ---
#
# Until 0.319.2 this check read commit subjects only, in a repository that carried
# a version tag per release. Each test below builds a real repository; the tags are
# made with explicit dates so "since the last cycle" does not depend on the clock.

def _tag(repo, name, when, annotated=False):
    """Tag HEAD as `name`, dated `when` (ISO). Lightweight tags take the commit's date.

    `tag.gpgSign=false` on the command line: a machine whose git signs every tag turns a
    plain `git tag <name>` into a signed one, which fails here with "no tag message?".
    """
    import os
    env = dict(os.environ, GIT_COMMITTER_DATE=when, GIT_AUTHOR_DATE=when)
    (repo / f"t-{name}.txt").write_text(name)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", f"work for {name}"],
                   check=True, capture_output=True, env=env)
    args = ["tag", "-a", name, "-m", name] if annotated else ["tag", name]
    subprocess.run(["git", "-C", str(repo), "-c", "tag.gpgSign=false", *args],
                   check=True, capture_output=True, env=env)


def _json_run(mod, capsys, *argv):
    import json as _json
    code = _run(mod, *argv, "--json")
    return code, _json.loads(capsys.readouterr().out)


def test_tags_are_counted_when_the_repository_has_them(scripts_path, tmp_path, capsys):
    """RED BEFORE 0.319.2: no subject names a version, so the subject scan read
    `no-releases-matched` while two minor releases were tagged."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "v1.1.0", "2026-02-01T12:00:00Z")
    _tag(project, "v1.2.0", "2026-03-01T12:00:00Z", annotated=True)

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "2")
    assert code == 1
    assert payload["status"] == "cycle-owed"
    assert payload["releases"] == 2
    assert payload["release_source"] == "tags"
    assert sorted(payload["release_tokens"]) == ["v1.1.0", "v1.2.0"]


def test_a_version_in_a_subject_is_not_a_release_when_tags_exist(scripts_path, tmp_path, capsys):
    """RED BEFORE 0.319.2: three subjects open with a minor version and were counted as
    three releases. The repository tagged one. The tag is the record."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "v1.1.0", "2026-02-01T12:00:00Z")
    for i, subject in enumerate(["1.2.0: planned", "1.3.0: drafted", "1.4.0: notes"]):
        (project / f"s{i}.txt").write_text(str(i))
        _git(project, "add", "-A")
        _git(project, "commit", "-q", "-m", subject)

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "3")
    assert code == 0
    assert payload["releases"] == 1
    assert payload["release_tokens"] == ["v1.1.0"]


def test_tags_before_the_last_cycle_and_patch_tags_are_not_counted(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _tag(project, "v1.0.0", "2025-06-01T12:00:00Z")      # before the cycle
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "v1.0.1", "2026-02-01T12:00:00Z")      # a patch
    _tag(project, "v1.1.0-rc1", "2026-02-02T12:00:00Z")  # not a version tag
    _tag(project, "v1.1.0", "2026-02-03T12:00:00Z")

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "5")
    assert code == 0
    assert payload["release_tokens"] == ["v1.1.0"]
    assert payload["tags_scanned"] == 3                   # the rc is not a version tag


def test_no_minor_tag_since_the_cycle_is_a_measured_zero(scripts_path, tmp_path, capsys):
    """Tags exist and none is new: `ok`, NOT `no-releases-matched`. The second means
    "my pattern may never have matched"; here the release record was read and is empty.
    Falling back to subjects in this case would count the mention below."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _tag(project, "v1.0.0", "2025-06-01T12:00:00Z")
    _cycles(project, "2026-01-01T00:00:00Z")
    (project / "later.txt").write_text("x")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "1.1.0: not released yet")

    code, payload = _json_run(mod, capsys, "--project-dir", str(project))
    assert code == 0
    assert payload["status"] == "ok"
    assert payload["releases"] == 0
    assert payload["release_source"] == "tags"
    assert payload["tags_scanned"] == 1


def test_without_version_tags_subjects_are_read_and_the_output_says_so(scripts_path, tmp_path, capsys):
    """The fallback, and the disclosure. A non-version tag does not switch the source."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["v0.1.0: one", "v0.2.0: two"])
    _git(project, "-c", "tag.gpgSign=false", "tag", "nightly")
    _cycles(project, "2000-01-01T00:00:00Z")

    assert _run(mod, "--project-dir", str(project), "--threshold", "5") == 0
    out = capsys.readouterr().out
    assert "2 minor release(s)" in out
    assert "read from commit subjects: the release repository has no version tags" in out

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "5")
    assert payload["release_source"] == "commit-subjects"
    assert payload["tags_scanned"] == 0


def test_the_text_output_names_the_tag_count_it_read(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "1.1.0", "2026-02-01T12:00:00Z")        # no `v`: still a version tag

    assert _run(mod, "--project-dir", str(project), "--threshold", "5") == 0
    out = capsys.readouterr().out
    assert "1 minor release(s)" in out
    assert "read from 1 version tag(s)" in out


def test_a_release_pattern_forces_the_subject_scan(scripts_path, tmp_path, capsys):
    """A pattern is a statement about subjects; giving one must not be silently ignored
    in a repository that happens to have tags."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["release 7.1", "release 7.2"])
    _cycles(project, "2000-01-01T00:00:00Z")
    _tag(project, "v1.1.0", "2026-02-01T12:00:00Z")

    code, payload = _json_run(mod, capsys, "--project-dir", str(project),
                              "--release-pattern", r"release (\d+)\.(\d+)", "--threshold", "5")
    assert payload["release_source"] == "commit-subjects"
    assert payload["releases"] == 2


def test_the_same_minor_tagged_with_and_without_v_is_one_release(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "v1.1.0", "2026-02-01T12:00:00Z")
    _tag(project, "1.1.0", "2026-02-02T12:00:00Z")

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "5")
    assert payload["releases"] == 1


def test_a_minor_line_first_tagged_as_a_patch_is_one_release(scripts_path, tmp_path, capsys):
    """A line can be first released as `.1`. Upstream's own history has three (0.192, 0.194,
    0.196: no `.0` tag exists); counting only tags that end in `.0` read three releases fewer
    than shipped. The later patch on the same line is not a second release, and a patch on a
    line first tagged BEFORE the cycle is not a release at all."""
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _tag(project, "v1.0.0", "2025-06-01T12:00:00Z")
    _cycles(project, "2026-01-01T00:00:00Z")
    _tag(project, "v1.0.1", "2026-02-01T12:00:00Z")      # old line, new patch: not a release
    _tag(project, "v1.1.1", "2026-02-02T12:00:00Z")      # new line, first tagged as a patch
    _tag(project, "v1.1.2", "2026-02-03T12:00:00Z")      # same line again

    code, payload = _json_run(mod, capsys, "--project-dir", str(project), "--threshold", "5")
    assert code == 0
    assert payload["releases"] == 1
    assert payload["release_tokens"] == ["v1.1.1"]


def test_never_recorded_counts_tags_too(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    project = _repo(tmp_path / "proj", ["chore: start"])
    _cycles(project)
    _tag(project, "v1.1.0", "2026-02-01T12:00:00Z")
    _tag(project, "v1.2.0", "2026-03-01T12:00:00Z")

    code, payload = _json_run(mod, capsys, "--project-dir", str(project))
    assert code == 1
    assert payload["status"] == "never-recorded"
    assert payload["releases"] == 2
