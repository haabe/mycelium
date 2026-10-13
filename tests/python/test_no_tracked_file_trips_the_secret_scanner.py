"""A commit of any file this repository tracks passes Mycelium's own commit scan (v0.323.1).

WHY THIS EXISTS. 0.323.0 made Mycelium refuse a commit or a push that carries a secret, with
gitleaks doing the scanning. Nobody ran that scan over Mycelium's own tree first. Run the day
after (dogfood 2026-10-13), it flagged four of this repository's test files: made-up values in the
shape of real credentials, there to test secret handling. So the scan refused any commit that
touched those lines, for the agent and, with the git hook, for a person, and the only way forward
was an ignore entry, which Mycelium tells the agent it may not write unasked.

The fix was to write each value so that the source holds no credential and the code under test
still receives one: put together from two halves at run time, or plain text where the value was
incidental. This test keeps it that way, by asking the shipped scan (`commit_scan.scan_staged`)
about a throwaway repository in which every tracked file is staged as new.

IF IT FAILS: do not add an ignore file, a scanner configuration or an inline allow comment. Write
the value in two halves (`"AKIA" + "..."`, or `"AKIA""..."` in a shell file) so that no scanner
sees it whole. If what the scanner found is real, it is a leak: rotate it.

LIMITS. Skipped where gitleaks is not installed, which includes CI today: without it the scan
falls back to Mycelium's own short list, which reads the first two million characters and names
one match, so it cannot answer for the whole tree. Run by hand on 2026-10-13, that list matches
one tracked line, the key a holdout eval scenario hands the agent on purpose
(`.claude/evals/scenarios/delivery/security-awareness.yml`); it was left as it is.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "mycelium" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _scratch_git  # noqa: E402
import commit_scan as cs  # noqa: E402


def _tracked() -> list[str] | None:
    try:
        done = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], text=True,
                              capture_output=True, check=False)
    except OSError:
        return None
    if done.returncode != 0:
        return None
    return [name for name in done.stdout.split("\0") if name]


def stage_as_new(names: list[str], source: Path, repo: Path) -> int:
    """Copy `names` from `source` into the throwaway `repo` and stage them. Returns how many."""
    copied = 0
    for name in names:
        src = source / name
        if src.is_symlink() or not src.is_file():
            continue
        dst = repo / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    subprocess.run(["git", "add", "-A"], cwd=repo, env=_scratch_git.clean_env(), check=True,
                   capture_output=True)
    return copied


@pytest.mark.skipif(cs.scanner() is None, reason="gitleaks is not installed")
def test_a_commit_of_every_tracked_file_passes_the_scan():
    tracked = _tracked()
    if not tracked:
        pytest.skip("not a git checkout: there is no list of tracked files to stage")
    with tempfile.TemporaryDirectory() as tmp:
        repo = _scratch_git.init(Path(tmp) / "tree")
        assert stage_as_new(tracked, ROOT, repo) > 0
        state, lines = cs.scan_staged(str(repo), False)
    assert state != "error", f"the scan itself failed: {lines}"
    assert state == "clean", (
        "Mycelium's own commit scan would refuse a commit that touches these tracked lines:\n  "
        + "\n  ".join(lines) + "\nWrite the value in two halves so no scanner sees it whole. Do "
        "not add an ignore file or an allow comment.")


@pytest.mark.skipif(cs.scanner() is None, reason="gitleaks is not installed")
def test_the_same_check_refuses_a_file_that_holds_a_made_up_key(tmp_path):
    """The check above can fail: one file with a key-shaped value, staged the same way."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "settings.py").write_text('AWS_KEY = "' + "AKIA" + "ABCDEFGHIJKLMNOP" + '"\n')
    repo = _scratch_git.init(tmp_path / "tree")
    assert stage_as_new(["settings.py", "not-there.py"], source, repo) == 1
    state, lines = cs.scan_staged(str(repo), False)
    assert state == "found" and any("settings.py" in line for line in lines), (state, lines)
