"""A throwaway git repository that is the directory the test made, or a loud failure (0.319.1).

WHY THIS EXISTS. On 2026-10-11 a `git push` from a git WORKTREE of this repository ran the suite
through the pre-push hook. In a worktree git exports `GIT_DIR=<main>/.git/worktrees/<name>` to its
hooks (in an ordinary checkout it exports no `GIT_DIR` at all, which is why nobody had seen this).
Every test that built a fixture with `git init` in a temp folder inherited that variable, and with
`GIT_DIR` set git does not look at the folder it is run in:

  - `git init` re-initialised the CALLER'S repository and wrote `core.bare = true` into its config;
  - `git config user.name t` wrote into the caller's config;
  - `git add -A` replaced the caller's index with the temp folder's files;
  - `git commit` put the fixture commits on the caller's checked-out branch.

Fourteen commits by "t <t@t>" landed on a feature branch, and the shared config said the
repository was bare. Twelve test files and three bash suites did this (traced file by file).

TWO LAYERS, BECAUSE ONE WAS NOT ENOUGH TO TRUST.
  1. `conftest.py` calls `clear_inherited_git_env()` before any test is collected, so the suite
     starts without the variables whoever started it happened to export.
  2. `init()` is how a test makes a repository. It runs `git init` with those variables removed
     whatever the process holds, then asks git, in the environment the test's NEXT commands will
     run in, where the repository is. If the answer is not inside the folder the test made, it
     raises before a single `config`, `add` or `commit` runs.

`test_suite_safe_in_a_worktree.py` holds both layers to it, and refuses a raw `git init` in a test.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

#: What points a child git at a repository, index or object store other than the one it stands
#: in. The first eight are named so a reader sees them; `git rev-parse --local-env-vars` is git's
#: own list (it prints the same names and whatever a later git adds) and is unioned in below.
REDIRECTING = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
)


class ScratchRepoEscapedError(RuntimeError):
    """git resolved a throwaway repository outside the folder made for it."""


def redirecting_names() -> tuple[str, ...]:
    """REDIRECTING plus git's own list of repository-local variables, when git can be asked."""
    env = {k: v for k, v in os.environ.items() if k not in REDIRECTING}
    try:
        out = subprocess.run(["git", "rev-parse", "--local-env-vars"], env=env,
                             capture_output=True, text=True, check=False).stdout
    except OSError:
        out = ""
    return tuple(dict.fromkeys([*REDIRECTING, *out.split()]))


def clean_env(env: dict | None = None) -> dict:
    """A copy of `env` (default: this process's) without the variables that redirect git."""
    names = set(redirecting_names())
    return {k: v for k, v in (os.environ if env is None else env).items() if k not in names}


def clear_inherited_git_env() -> list[str]:
    """Remove the redirecting variables from this process; returns the names that were set."""
    removed = [name for name in redirecting_names() if name in os.environ]
    for name in removed:
        del os.environ[name]
    return removed


def init(path, *args: str) -> Path:
    """`git init` in `path`, which must then BE the repository. Raises ScratchRepoEscapedError
    when git, asked in this process's own environment, resolves it anywhere else."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", *args], cwd=path, env=clean_env(), check=True,
                   capture_output=True)
    asked = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], cwd=path,
                           capture_output=True, text=True, check=False)
    inside = os.path.realpath(path)
    where = os.path.realpath(asked.stdout.strip()) if asked.stdout.strip() else ""
    if asked.returncode != 0 or not (where == inside or where.startswith(inside + os.sep)):
        held = sorted(n for n in redirecting_names() if n in os.environ)
        raise ScratchRepoEscapedError(
            f"The throwaway repository made in {inside} is not where git looks from there: git "
            f"resolves {where or asked.stderr.strip() or 'nothing'}. Every later git command in "
            f"this test would act on THAT repository. Variables redirecting git in this process: "
            f"{', '.join(held) or 'none found'}. Nothing was configured or committed.")
    return path
