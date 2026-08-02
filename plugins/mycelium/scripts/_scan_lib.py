"""Shared tree-walk helpers for the wiring/authenticity fitness functions.

Extracted rather than duplicated (G-V3), and separate from `_text_lib.py`
because that file answers questions about the CONTENT of a line while this one
answers whether a file is ours to judge at all.

THE DEFECT THIS EXISTS FOR (dogfood 2026-08-02). Both `check_wiring_contract.py`
and `check_test_authenticity.py` carried `"fixtures"` in `SKIP_DIRS`, with a
comment explaining exactly why: fixture trees are synthetic mini-repos built to
make a guard fire, so governing them "proposes rules about scaffolding and
buries the real findings". The intent was right. The dogfood repo's directory is
`.fixtures`, with a leading dot, and `part in SKIP_DIRS` is exact-match. So:

  * `--detect` produced 96 contract rules of which **3 were ours** and 93
    governed two vendored third-party repos, every one at `confidence: 1.0`.
    Committing that draft would have created a contract that passes forever
    while describing somebody else's code — a green result measuring the wrong
    tree, which is the precise failure the fitness functions exist to catch.
  * `check_test_authenticity` FAILED with three findings, all of them tests
    inside that vendored code. A check that fails loudly on code outside its
    remit erodes trust as surely as one that passes blindly.

A NAME LIST WAS NEVER GOING TO HOLD. Adding `.fixtures` fixes today and leaves
`_fixtures`, `third_party`, `.cache`, and whatever the next project calls it.
The general question is "is this file part of this project?", and the repository
already answers it: **git ignores it and does not track it.** That is one
subprocess call and it is correct by construction, where an enumeration is
correct until the next directory name.

The predicate is `--others --ignored --exclude-standard`: ignored AND untracked.
A force-added file that matches an ignore rule is still ours and stays in scope.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # `Path` appears only in annotations, which `from __future__
    from pathlib import Path  # import annotations` defers to strings at runtime


def ignored_paths(root: Path) -> set[Path]:
    """Absolute paths under `root` that git ignores and does not track.

    Returns an EMPTY SET when the answer cannot be determined — not a git repo,
    git missing, or the call failed. Empty means "skip nothing", so the caller
    falls back to its previous behaviour of scanning everything. Failing open is
    right here: this filter exists to remove noise, and a project without git
    should still get its checks run rather than silently get none.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard",
             "--directory", "-z"],
            cwd=root, capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if out.returncode != 0:
        return set()
    return {
        (root / rel).resolve()
        for rel in out.stdout.split("\0")
        if rel.strip()
    }


def is_ignored(path: Path, ignored: set[Path]) -> bool:
    """True when `path` is, or sits beneath, a git-ignored untracked path.

    `--directory` collapses a wholly-ignored directory to one entry, so a
    membership test alone would miss every file inside it — which is the common
    case and the one that produced the 93 vendored rules.
    """
    if not ignored:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return any(p == resolved or p in resolved.parents for p in ignored)
