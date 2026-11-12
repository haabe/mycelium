#!/usr/bin/env python3
"""check_record_size.py — canonical records too large for one Read, and how fast they grow.

WHY THIS EXISTS (founder ruling 2026-11-12, "Size warning only"). The runtime logs in
.claude/state/ are bounded (prune_state_logs.py keeps 90 days); the committed records are not.
Measured on the maintainer's project 2026-10-20: human-tasks.yml 2,205 KB (+307 KB in 30 days),
decision-log.md 4,180 KB (+458), corrections.md 922 KB (+109). No agent reads a file like that
whole: every decision about it rests on a grep or an offset slice, which is the setting of the
absence-claim and stale-read mistakes. Nothing reported the size, so the person saw it as the
agent forgetting, not as a file the agent cannot read.

THE THRESHOLD, AND WHERE IT COMES FROM. READ_LIMIT_BYTES is 256 KB: Claude Code's Read tool
refuses a file larger than that. Measured on the maintainer's
project 2026-10-16, when corrections.md at 929 KB could not be read whole; docs/ai-system-card.md
section 6 states the same finding as the file having "grown past what the Read tool accepts". It
is a floor, not the whole problem: the Read tool also caps what one call returns by its token
count, so a file under 256 KB can still come back cut, and a clean line is not proof that every
record reads whole. Another runtime's limit may differ; the number is the one this framework has
measured.

WHAT IT READS. The canonical records: `.claude/canvas/*.yml`, `.claude/diamonds/*.yml`,
`.claude/memory/*.md` and `.claude/harness/*.md|*.yml` (decision-log.md, corrections.md,
human-tasks.yml, cycle-history.yml and their siblings). Not `.claude/state/`, which is pruned.
Growth is the size now against the size in the commit that was HEAD `--days` ago (git), said only
when git can answer.

REPORT ONLY. Nothing is moved, trimmed or archived; whether and how a record is split is a
separate decision the person makes. Exit 0 always.

  check_record_size.py [--project-dir .] [--days 30]   the report, for /mycelium:canvas-health
  check_record_size.py --advisory                       one line, only when a record is past the
                                                        threshold (session-start.sh relays it)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

#: Claude Code's Read tool refuses a file over 256 KB (measured 2026-10-16;
#: see the docstring for the source and for what this number does not cover).
READ_LIMIT_BYTES = 256 * 1024
RECORD_GLOBS = (".claude/canvas/*.yml", ".claude/diamonds/*.yml", ".claude/memory/*.md",
                ".claude/harness/*.md", ".claude/harness/*.yml")
ADVISORY_HEAD = "RECORDS PAST ONE READ"
#: The session-start line names the largest few; canvas-health lists every one.
ADVISORY_SHOWN = 5


def records(root: Path) -> list[Path]:
    out: list[Path] = []
    for pat in RECORD_GLOBS:
        out += [p for p in root.glob(pat) if p.is_file()]
    return sorted(set(out))


def _git(root: Path, *args: str, stdin: str = "") -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], input=stdin, capture_output=True,
                           text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""  # SPEAKS: growth is then left out of the line, which says it is unknown
    return r.stdout if r.returncode == 0 else ""


def sizes_then(root: Path, rels: list[str], days: int) -> dict[str, int] | None:
    """Each path's size in the commit that was HEAD `days` ago: -1 when it did not exist then.
    None when git cannot say (no repository, or no commit that old)."""
    if not rels:
        return {}
    rev = _git(root, "rev-list", "-1", f"--before={int(time.time()) - days * 86400}",
               "HEAD").strip()
    if not rev:
        return None
    out = _git(root, "cat-file", "--batch-check=%(objectsize)",
               stdin="".join(f"{rev}:{r}\n" for r in rels)).splitlines()
    if len(out) != len(rels):
        return None
    return {r: (int(line) if line.strip().isdigit() else -1) for r, line in zip(rels, out)}


def _kb(n: int) -> str:
    return f"{round(n / 1024):,} KB"


def past_limit(root: Path, days: int, limit: int = READ_LIMIT_BYTES) -> list[str]:
    """One phrase per record past `limit`, largest first: path, size, growth."""
    big = [(p.stat().st_size, p) for p in records(root)]
    big = sorted(((n, p) for n, p in big if n > limit), key=lambda t: -t[0])
    rels = [str(p.relative_to(root)) for _, p in big]
    then = sizes_then(root, rels, days)
    out = []
    for (n, _), rel in zip(big, rels):
        if then is None:
            grew = "growth unknown: git has no commit that old here, or could not be run"
        elif then.get(rel, -1) < 0:
            grew = f"new in the last {days} days"
        else:
            d = n - then[rel]
            grew = f"{'+' if d >= 0 else '-'}{_kb(abs(d))} in {days} days"
        out.append(f"{rel} {_kb(n)} ({grew})")
    return out


def advisory(found: list[str]) -> str:
    limit = _kb(READ_LIMIT_BYTES)
    return (f"{ADVISORY_HEAD}: {len(found)} record file(s) are larger than the {limit} "
            "the Read tool returns whole, so an agent reads them in slices or by search and can "
            f"miss what it did not reach: {'; '.join(found[:ADVISORY_SHOWN])}"
            + (f"; and {len(found) - ADVISORY_SHOWN} more (/mycelium:canvas-health lists them)"
               if len(found) > ADVISORY_SHOWN else "")
            + ". Report only; nothing is moved. Before saying a record holds or lacks something, "
            "search the whole file. ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--advisory", action="store_true",
                    help="print one line only when a record is past the threshold")
    args = ap.parse_args(argv)
    root = Path(args.project_dir).resolve()
    if not (root / ".claude").is_dir():
        if not args.advisory:
            print("record size: N/A (no .claude/ directory here)")
        return 0
    found = past_limit(root, args.days)
    if args.advisory:
        if found:
            print(advisory(found))
        return 0
    n = len(records(root))
    if not found:
        print(f"record size: OK, none of {n} record file(s) is past {_kb(READ_LIMIT_BYTES)} "
              "(the Read tool's whole-file limit; a smaller file can still be cut by its token "
              "count)")
        return 0
    print(f"record size: {len(found)} of {n} record file(s) past {_kb(READ_LIMIT_BYTES)}, the "
          "Read tool's whole-file limit. Report only; nothing is moved.")
    for line in found:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
