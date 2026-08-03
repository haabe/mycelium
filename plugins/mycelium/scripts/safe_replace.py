#!/usr/bin/env python3
"""All-or-nothing multi-file text replacement: validate every anchor, then write.

WHY (dogfood 2026-08-03). The standing rule for scripted edits is "assert the
replacement landed, then re-read", written because `str.replace` anchors had
silently missed. Following it produced a WORSE failure than ignoring it: a script
patching two files with a shared anchor wrote the first, then raised on the
second, leaving the tree half-edited. The two files were assumed to be verbatim
mirrors and were not — one carried abbreviated copies of the same rules.

The bug is ORDERING, not the assertion. `write; assert` converts a bad assertion
into a half-applied edit, which is strictly worse than no assertion at all,
because now the tree is in a state nobody described. `validate-all; then write`
cannot do that: either every anchor is found and every file is written, or
nothing is touched and the caller is told which anchor failed.

Same session, the same shape produced five more failures — occurrence counts
asserted from memory (`== 3` when it was 2, twice; `== 4` when it was 3), each
aborting a script that had already written. Passing the expected count here makes
it a precondition instead of an afterthought, and getting it wrong costs a clear
error rather than a partial edit.

USAGE

  As a library — the intended path for agent-authored edits:

      from safe_replace import apply_edits
      apply_edits([
          {"path": "a.md", "old": "foo", "new": "bar"},              # expect 1
          {"path": "b.md", "old": "baz", "new": "qux", "count": 2},  # expect 2
      ])

  As a CLI, taking a JSON spec on stdin or via --spec:

      echo '[{"path":"a.md","old":"foo","new":"bar"}]' | safe_replace.py
      safe_replace.py --spec edits.json --dry-run

`count` defaults to 1 — the overwhelmingly common intent, and the one whose
violation is most often a silently-wrong anchor. Pass `count: 0` to assert an
anchor is ABSENT (a no-op edit used as a precondition), or an explicit integer.

Exit codes:
  0 — every anchor validated and every file written (or --dry-run reported clean)
  1 — at least one anchor failed; NOTHING was written
  2 — malformed spec
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class AnchorError(Exception):
    """One or more anchors did not match. Raised before anything is written."""


def _validate(edits: list[dict]) -> list[tuple[Path, str, str]]:
    """Check every anchor against current file contents. Write nothing.

    Returns the resolved plan. Raises AnchorError listing EVERY failure rather
    than the first, so one run tells the caller all of what is wrong — a
    fail-fast here would just produce the same guessing game one anchor at a time.
    """
    problems: list[str] = []
    plan: list[tuple[Path, str, str]] = []
    # Group by path so several edits to one file compose correctly: each is
    # validated against the text as the PREVIOUS edits in this spec leave it,
    # not against the original, or a second edit to the same file would be
    # validated against text that will never exist.
    staged: dict[Path, str] = {}

    for i, edit in enumerate(edits):
        if not isinstance(edit, dict):
            problems.append(f"edit {i}: not an object")
            continue
        missing = [k for k in ("path", "old", "new") if k not in edit]
        if missing:
            problems.append(f"edit {i}: missing {', '.join(missing)}")
            continue
        path = Path(edit["path"])
        old, new = edit["old"], edit["new"]
        expected = edit.get("count", 1)
        if not isinstance(expected, int) or expected < 0:
            problems.append(f"edit {i} ({path}): count must be a non-negative int")
            continue
        if path not in staged:
            if not path.is_file():
                problems.append(f"edit {i}: {path} does not exist")
                continue
            staged[path] = path.read_text()
        found = staged[path].count(old)
        if found != expected:
            problems.append(
                f"edit {i} ({path}): anchor occurs {found} time(s), expected "
                f"{expected}. Anchor starts: {old[:70]!r}"
            )
            continue
        if expected:
            staged[path] = staged[path].replace(old, new)
        plan.append((path, old, new))

    if problems:
        raise AnchorError(
            f"{len(problems)} anchor problem(s); NOTHING was written:\n  "
            + "\n  ".join(problems)
        )
    return [(p, staged[p], "") for p in staged]


def apply_edits(edits: list[dict], dry_run: bool = False) -> list[Path]:
    """Validate every anchor, then write every file. Returns paths written."""
    resolved = _validate(edits)
    if dry_run:
        return [p for p, _, _ in resolved]
    written = []
    for path, text, _ in resolved:
        path.write_text(text)
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", help="JSON file of edits; omit to read stdin")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate every anchor and write nothing")
    args = ap.parse_args(argv)

    raw = Path(args.spec).read_text() if args.spec else sys.stdin.read()
    try:
        edits = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"safe_replace: spec is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(edits, list):
        print("safe_replace: spec must be a JSON array of edit objects",
              file=sys.stderr)
        return 2

    try:
        written = apply_edits(edits, dry_run=args.dry_run)
    except AnchorError as exc:
        print(f"safe_replace: {exc}", file=sys.stderr)
        return 1

    verb = "would write" if args.dry_run else "wrote"
    print(f"safe_replace: {len(edits)} edit(s) validated, {verb} "
          f"{len(written)} file(s): {', '.join(str(p) for p in written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
