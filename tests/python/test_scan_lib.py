"""Coverage tests for _scan_lib.py — the git-ignore filter on the fitness functions (G-V12).

THE DEFECT (dogfood 2026-08-02). Both `check_wiring_contract.py` and
`check_test_authenticity.py` carried `"fixtures"` in `SKIP_DIRS`, with a comment
saying exactly why fixture trees must not be governed. The dogfood repo's
directory is `.fixtures`, with a leading dot, and the membership test is exact.
So the guard was written, correct in intent, and blind to the one tree it was
written for.

What that produced, measured rather than supposed:

  * `check_wiring_contract --detect` returned **96 contract rules, of which 3
    were ours** — 93 governed two vendored third-party repos, every one at
    `confidence: 1.0`. Committing that draft would have created a contract that
    passes forever while describing somebody else's code. A green result
    measuring the wrong tree is the precise failure these functions exist for.
  * `check_test_authenticity` FAILED with three findings, all tests inside that
    vendored code. Failing loudly on code outside your remit erodes trust as
    surely as passing blindly does.

WHY A NAME LIST WAS NOT THE FIX. Adding `.fixtures` closes today and leaves
`_fixtures`, `third_party`, `.cache`, and whatever the next project calls it.
The general question is "is this file part of this project?", and the repository
already answers it. `.fixtures` was added anyway as belt-and-braces for
non-git checkouts, where `ignored_paths` correctly returns nothing.

Scenario-per-guardpost:
  happy  — plain repo, nothing ignored          -> empty set, nothing skipped
  sad    — ignored directory                    -> every file beneath it skipped
  bad    — not a git repo                       -> empty set, no crash, scan everything
  bad    — git absent / call fails              -> empty set, no crash
  edge   — TRACKED file matching an ignore rule -> NOT skipped, it is ours
  edge   — ignored file beside a tracked one    -> only the ignored one skipped
"""
import subprocess
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import _scan_lib

    return _scan_lib


SCRIPTS = "plugins/mycelium/scripts"


def _repo(tmp_path, gitignore=None):
    """A real git repo. The predicate is git's, so the fixture must be too."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.local"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    if gitignore is not None:
        (tmp_path / ".gitignore").write_text(gitignore)
    return tmp_path


def _write(p, text="x"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


# ------------------------------------------------------------------ happy


def test_plain_repo_ignores_nothing(tmp_path, request):
    lib = _import(request.config.rootpath / SCRIPTS)
    root = _repo(tmp_path, gitignore="")
    f = _write(root / "src" / "a.py")
    assert lib.ignored_paths(root) == set()
    assert lib.is_ignored(f, lib.ignored_paths(root)) is False


# ------------------------------------------------------------------ sad


def test_files_inside_an_ignored_directory_are_skipped(tmp_path, request):
    """The load-bearing case: `--directory` collapses a wholly-ignored tree to
    ONE entry, so a plain membership test misses every file inside it. That is
    exactly what produced 93 vendored contract rules."""
    lib = _import(request.config.rootpath / SCRIPTS)
    root = _repo(tmp_path, gitignore=".fixtures/\n")
    buried = _write(root / ".fixtures" / "vendored" / "deep" / "mod.py")
    ignored = lib.ignored_paths(root)
    assert ignored, "an ignored directory must be reported"
    assert lib.is_ignored(buried, ignored) is True


def test_only_the_ignored_sibling_is_skipped(tmp_path, request):
    lib = _import(request.config.rootpath / SCRIPTS)
    root = _repo(tmp_path, gitignore="secret.py\n")
    ours = _write(root / "keep.py")
    theirs = _write(root / "secret.py")
    ignored = lib.ignored_paths(root)
    assert lib.is_ignored(theirs, ignored) is True
    assert lib.is_ignored(ours, ignored) is False


# ------------------------------------------------------------------ bad


def test_not_a_git_repo_returns_empty_and_does_not_crash(tmp_path, request):
    """Fails OPEN by design. This filter removes noise; a project without git
    should still get its checks run rather than silently get none."""
    lib = _import(request.config.rootpath / SCRIPTS)
    _write(tmp_path / "a.py")
    assert lib.ignored_paths(tmp_path) == set()


def test_git_missing_returns_empty_and_does_not_crash(tmp_path, request, monkeypatch):
    lib = _import(request.config.rootpath / SCRIPTS)

    def boom(*_a, **_k):
        raise OSError("git not found")

    monkeypatch.setattr(lib.subprocess, "run", boom)
    assert lib.ignored_paths(tmp_path) == set()


def test_empty_ignore_set_short_circuits(tmp_path, request):
    lib = _import(request.config.rootpath / SCRIPTS)
    assert lib.is_ignored(tmp_path / "anything.py", set()) is False


# ------------------------------------------------------------------ edge


def test_tracked_file_matching_an_ignore_rule_stays_in_scope(tmp_path, request):
    """A force-added file is ours however the ignore rules read. The predicate is
    ignored AND untracked, not ignored alone — get this wrong and a project that
    force-adds a generated-but-owned file silently loses coverage on it."""
    lib = _import(request.config.rootpath / SCRIPTS)
    root = _repo(tmp_path, gitignore="build/\n")
    forced = _write(root / "build" / "owned.py")
    subprocess.run(["git", "add", "-f", "build/owned.py"], cwd=root, check=True)
    ignored = lib.ignored_paths(root)
    assert lib.is_ignored(forced, ignored) is False
