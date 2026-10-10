#!/usr/bin/env python3
"""`.claude/state/` never exists without its ignore file (v0.318.0).

WHY. The hooks write logs there on almost every tool call (files read and changed, guard fires,
failures, search terms), in any project the plugin runs in, including one that never ran
/mycelium:setup, which until now was the only writer of `.claude/state/.gitignore`. Verified
2026-10-10: one Read in a bare git repo created `.claude/state/read-log.jsonl` with no ignore
file, so `git add -A` committed it. Found by Anthropic's plugin directory review of v0.317.4.

Two halves, one rule set (`state-gitignore.txt`, next to this file):
  * `ensure(state_dir)` for Python writers: create the folder and its ignore file together.
  * `scripts/_hook_prelude.sh`, sourced by every hook, writes the same file when the hook
    exits and finds the folder without it, whoever created it (a Python script the hook
    called, an older version, another tool). It never creates the folder itself, and in a
    project with no `.claude/canvas/` or `.claude/diamonds/` the hook does nothing at all.

An ignore file that already exists is never rewritten: a user's own edits to it stand.

CLI (used by /mycelium:setup): _state_dir.py --project-dir DIR  -> creates DIR/.claude/state
and its ignore file if missing; prints the path. Exit 0.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "state-gitignore.txt"


def write_ignore(state_dir: Path) -> bool:
    """Write the ignore file into an existing state folder if it has none; True if written."""
    target = state_dir / ".gitignore"
    if not state_dir.is_dir() or target.exists():
        return False
    try:
        # O_EXCL: two hooks racing on the same new folder write it once, never interleaved.
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except OSError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.read_text(encoding="utf-8"))
    return True


def ensure(state_dir: Path) -> Path:
    """Create the state folder if needed, with its ignore file; return it."""
    state_dir.mkdir(parents=True, exist_ok=True)
    write_ignore(state_dir)
    return state_dir


def _state_root(path: Path) -> Path | None:
    for p in (path, *path.parents):
        if p.name == "state" and p.parent.name == ".claude":
            return p
    return None


def prepare_dir(directory: Path) -> Path:
    """`directory.mkdir(parents=True, exist_ok=True)`, and if it is or lies inside a
    `.claude/state` folder, that folder gets its ignore file. Every Mycelium script creates
    folders through this or `prepare` (tests/python/test_state_ignore.py holds that)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    root = _state_root(directory)
    if root is not None:
        write_ignore(root)
    return directory


def prepare(path: Path) -> Path:
    """Create the folder a file is about to be written into (see prepare_dir); return the path."""
    prepare_dir(Path(path).parent)
    return Path(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create .claude/state with its ignore file.")
    ap.add_argument("--project-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    print(ensure(args.project_dir / ".claude" / "state"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
