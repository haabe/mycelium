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

WHAT THAT RULE COSTS, AND WHO IS TOLD (v0.322.2). The rules keep a few files IN git because each
records a decision the person made (the skip and lock acks, `upstream.json`). A name added to the
rules later never reaches an ignore file that already exists, so there the decision is ignored by
git and a fresh clone is asked again. `scale-lock-ack` (0.245.0) was missing from the rules
altogether until 0.322.2. `ignored_decisions()` finds a decision file that exists and that git
ignores, and session start says so with the one line to add. The ignore file is still not touched.

CLI (used by /mycelium:setup): _state_dir.py --project-dir DIR  -> creates DIR/.claude/state
and its ignore file if missing; prints the path. Exit 0.
_state_dir.py --project-dir DIR --ignored-decisions  -> creates nothing; prints the session-start
reminder when a decision file there is ignored by git, else nothing. Exit 0.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
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


#: `git check-ignore -v` names a rule as file, line and pattern.
_RULE_PARTS = 3
#: Kept by the rules for the folder's own sake, not because they record a decision.
_NOT_DECISIONS = (".gitignore", "README.md")


def decision_files() -> list[str]:
    """The files the rules keep in git because each records a decision of the person's."""
    keep = [line[1:].strip() for line in TEMPLATE.read_text(encoding="utf-8").splitlines()
            if line.startswith("!")]
    return [name for name in keep if name not in _NOT_DECISIONS]


def ignored_decisions(project_dir: Path) -> tuple[list[str], str]:
    """(decision files that exist under `project_dir` and that the state folder's OWN ignore file
    ignores, a note when git could not be asked). A tracked file is never reported: `git
    check-ignore` answers for untracked paths only. No git, or no repository, is not a finding and
    gives ([], ""). Neither is a rule from anywhere else (a root `.gitignore` that leaves out all
    of `.claude/`, the person's global excludes): that is the person's choice about their
    repository, and one more line in the state folder's file would not change it."""
    state = Path(project_dir) / ".claude" / "state"
    present = [name for name in decision_files() if (state / name).is_file()]
    if not present or shutil.which("git") is None:
        return [], ""
    ignored: list[str] = []
    for name in present:
        try:
            done = subprocess.run(
                ["git", "-C", str(project_dir), "check-ignore", "-v", "--",
                 f".claude/state/{name}"], capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError) as e:
            return ignored, (f"Mycelium could not ask git whether .claude/state/{name} is ignored "
                             f"({type(e).__name__}); nothing is known about the files not listed.")
        # `<file with the rule>:<line>:<pattern>\t<path>`. With -v git prints the LAST rule that
        # matched and exits 0 for it even when that rule is a `!keep`, so the pattern is read too.
        rule = done.stdout.split("\t", 1)[0].rsplit(":", 2)
        if done.returncode != 0 or len(rule) != _RULE_PARTS:
            continue
        source, pattern = rule[0].replace("\\", "/"), rule[2]
        if source.endswith(".claude/state/.gitignore") and not pattern.startswith("!"):
            ignored.append(name)
    return ignored, ""


def ignored_decisions_line(project_dir: Path) -> str:
    """The session-start reminder, or "" when there is nothing to say."""
    ignored, note = ignored_decisions(project_dir)
    if not ignored:
        return note
    files = ", ".join(f".claude/state/{name}" for name in ignored)
    lines = " and ".join(f"`!{name}`" for name in ignored)
    verb, noun = ("records", "it") if len(ignored) == 1 else ("record", "them")
    said = (f"DECISION FILE NOT IN GIT: {files} {verb} a decision the person made here, and this "
            f"project's .claude/state/.gitignore ignores {noun}. A fresh clone or a second machine "
            f"will not have {noun}, and the same question will be asked again. Mycelium never "
            f"rewrites an ignore file that exists. Tell the person in one line and offer to add "
            f"{lines} to .claude/state/.gitignore. Whether to commit {noun} is theirs to decide: "
            f"the file holds their own words.")
    return f"{said} {note}".strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Create .claude/state with its ignore file.")
    ap.add_argument("--project-dir", required=True, type=Path)
    ap.add_argument("--ignored-decisions", action="store_true",
                    help="create nothing; print the reminder when git ignores a decision file")
    args = ap.parse_args(argv)
    if args.ignored_decisions:
        line = ignored_decisions_line(args.project_dir)
        if line:
            print(line)
        return 0
    print(ensure(args.project_dir / ".claude" / "state"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
