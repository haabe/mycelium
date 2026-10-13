"""Install a git pre-commit hook that scans what is staged for secrets (v0.323.0).

WHY THIS EXISTS. Mycelium's own hooks scan a commit or push the AGENT makes
(`scripts/commit_scan.py`). They never see a commit the person makes in their own terminal. This
puts the same scan in git itself, for this clone. `/mycelium:setup` offers it; nothing installs it
unasked. Git hooks are not cloned, so each clone needs it once.

It never overwrites a hook that is already there: it says what to add to it instead.

Usage: install_git_secret_hook.py [--project-dir DIR] [--check]
  exit 0  installed, or a hook that already runs a scanner is in place
  exit 1  a different pre-commit hook exists; nothing was written, the lines to add are printed
  exit 2  not a git repository, or the hook could not be written
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

# ONE BLOCK, USED BOTH WAYS (0.323.1): it is the body of the hook this script writes, and it is
# what the script prints for a hook that is already there. Until 0.323.1 the printed text was a
# different line, `command -v gitleaks ... && gitleaks ... || exit 1`, which exits 1 when
# gitleaks is NOT installed. Pasted into a team's hook it refused every commit on a machine
# without the scanner, where the written hook says the commit was not scanned and lets it
# through. It had never been run with no scanner on the path.
SCAN = """if command -v gitleaks >/dev/null 2>&1; then
  gitleaks git --pre-commit --staged --redact --no-banner || exit 1
else
  echo "Mycelium: gitleaks is not installed, so this commit was not scanned for secrets." >&2
  echo "Install it: https://github.com/gitleaks/gitleaks" >&2
fi
"""
HOOK = """#!/bin/sh
# Installed by Mycelium (/mycelium:setup). Scans what is staged for secrets before a commit.
# Git hooks are not cloned: run /mycelium:setup again in a fresh clone to install it there.
""" + SCAN


def hook_path(project_dir: str) -> Path | None:
    try:
        done = subprocess.run(["git", "-C", project_dir, "rev-parse", "--git-path",
                               "hooks/pre-commit"], text=True, capture_output=True, check=False)
    except OSError:
        return None  # SPEAKS: main() says this is not a git repository
    if done.returncode != 0 or not done.stdout.strip():
        return None
    path = Path(done.stdout.strip())
    return path if path.is_absolute() else Path(project_dir, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--check", action="store_true", help="say what is there; write nothing")
    args = ap.parse_args(argv)
    path = hook_path(args.project_dir)
    if path is None:
        print("Not a git repository: there is no commit to scan here.")
        return 2
    if path.exists():
        if "gitleaks" in path.read_text(encoding="utf-8", errors="replace"):
            print(f"{path} already runs gitleaks. Nothing to do.")
            return 0
        print(f"{path} exists and is yours; it was not changed. To scan for secrets, add these "
              f"lines to it before its own checks:\n{SCAN}")
        return 1
    if args.check:
        print(f"No pre-commit hook yet. This would write {path}.")
        return 0
    try:
        os.makedirs(path.parent, exist_ok=True)  # git's own hooks folder, not Mycelium's state
        path.write_text(HOOK, encoding="utf-8")
        path.chmod(0o755)
    except OSError as exc:
        print(f"Could not write {path}: {type(exc).__name__}.")
        return 2
    print(f"Wrote {path}. Commits made in this clone are now scanned for secrets by gitleaks, "
          "when it is installed. Other clones need this run again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
