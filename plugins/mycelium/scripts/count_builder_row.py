#!/usr/bin/env python3
"""Print a builder's own north-star row from their own record. Nothing is sent anywhere.

WHY THIS EXISTS. The framework's north star (dogfood DL-1177, 2026-09-07) is a hypothesis
whose unit lives in a builder's own repository: one build-or-kill decision, in the discovery
layer, citing evidence from outside the builder, made before the project's first source
file. There is no telemetry by design (PRIVACY.md), so the maintainer's proxy sheet gained
its first row by reading a public repo by hand. This is the opt-in half: a builder runs it,
reads one line, and pastes it where they like or not at all.

WHAT IT COUNTS, AND WHICH PARTS ARE PROXIES, said in the output so the line is not read as
more than it is:

  * first source file: the date of the first commit that added a file outside `.claude/`
    and `docs/` with a code extension (git history; "unknown" without git or without such a
    file, and then nothing is "before" it).
  * decisions before first source: dated entries in `.claude/harness/decision-log.md` (a
    heading carrying a date) dated on or before that day.
  * of which citing outside evidence: PROXY. An entry whose text carries a URL, a
    `source_class: external_*` marker, a `(per ...)` citation or an interview word. The unit
    asks for a person in the pipeline or a fact about the market; a lexical proxy cannot
    tell that from a link to one's own notes, so the number is an upper bound.
  * kills before code: cycle-history rows with terminal_state `killed` or `archived`
    completed on or before the first-source day, plus archived-solutions entries dated so.
  * sessions: distinct session ids in the read-log and change-log the hooks write.

The discovery-layer condition (L0 to L2) is NOT applied: decision-log entries carry no
scale, and guessing one would manufacture the count. The line says so.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_HEADING = re.compile(r"^#{2,3} ")
_OUTSIDE = re.compile(r"https?://|source_class:\s*external_|\(per\b|\binterview|\breplied\b|"
                      r"\bsaid\b|\btranscript\b", re.IGNORECASE)
_CODE_EXT = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".swift",
             ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".cs", ".sh", ".sql", ".ex", ".exs",
             ".scala", ".clj", ".hs", ".lua", ".dart", ".vue", ".svelte", ".html", ".css")
_TERMINAL_KILL = ("killed", "archived")


def first_source_date(project: Path) -> date | None:
    """Date of the first commit adding a code file outside .claude/ and docs/, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--name-only",
             "--reverse", "--", ".", ":!.claude", ":!docs"],
            cwd=project, capture_output=True, text=True, check=False, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    current: date | None = None
    for line in out.splitlines():
        m = _DATE.fullmatch(line.strip())
        if m:
            current = date.fromisoformat(m.group(1))
            continue
        if current and line.strip().lower().endswith(_CODE_EXT):
            return current
    return None


def decisions(project: Path) -> list[tuple[date, str]]:
    """(date, text) per dated heading entry in the decision log."""
    path = project / ".claude" / "harness" / "decision-log.md"
    if not path.is_file():
        return []
    out: list[tuple[date, str]] = []
    current: tuple[date, list[str]] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if _HEADING.match(line):
            if current:
                out.append((current[0], "\n".join(current[1])))
            m = _DATE.search(line)
            current = (date.fromisoformat(m.group(1)), [line]) if m else None
        elif current:
            current[1].append(line)
    if current:
        out.append((current[0], "\n".join(current[1])))
    return out


def kills(project: Path, cutoff: date | None) -> int:
    n = 0
    canvas = project / ".claude" / "canvas"
    try:
        cyc = yaml.safe_load((canvas / "cycle-history.yml").read_text(encoding="utf-8")) or {}
        for c in (cyc.get("cycles") or []) if isinstance(cyc, dict) else []:
            if not isinstance(c, dict) or c.get("terminal_state") not in _TERMINAL_KILL:
                continue
            m = _DATE.search(str(c.get("completed_at") or ""))
            if m and (cutoff is None or date.fromisoformat(m.group(1)) <= cutoff):
                n += 1
    except (OSError, yaml.YAMLError, ValueError):
        pass
    try:
        arc = yaml.safe_load((canvas / "archived-solutions.yml").read_text(encoding="utf-8")) or {}
        for a in (arc.get("archived") or []) if isinstance(arc, dict) else []:
            if not isinstance(a, dict):
                continue
            m = _DATE.search(str(a.get("archived_at") or a.get("date") or ""))
            if m and (cutoff is None or date.fromisoformat(m.group(1)) <= cutoff):
                n += 1
    except (OSError, yaml.YAMLError, ValueError):
        pass
    return n


def sessions(project: Path) -> int:
    ids: set[str] = set()
    for name in ("read-log.jsonl", "change-log.jsonl"):
        path = project / ".claude" / "state" / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                sid = json.loads(line).get("session_id")
            except (ValueError, AttributeError):
                continue
            if sid:
                ids.add(str(sid))
    return len(ids)


def row(project: Path) -> dict:
    first = first_source_date(project)
    decs = decisions(project)
    before = [(d, t) for d, t in decs if first is not None and d <= first]
    return {
        "first_source": str(first) if first else "unknown",
        "decisions_total": len(decs),
        "decisions_before_first_source": len(before),
        "citing_outside_evidence": sum(1 for _, t in before if _OUTSIDE.search(t)),
        "kills_before_code": kills(project, first) if first else 0,
        "sessions": sessions(project),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    project = Path(args.project_dir)
    if not (project / ".claude" / "harness" / "decision-log.md").is_file():
        print("NOT A PASS: no .claude/harness/decision-log.md; there is no record to count.")
        return 1
    r = row(project)
    if args.json:
        print(json.dumps(r))
        return 0
    print(f"mycelium row | first source file {r['first_source']} | decisions before it "
          f"{r['decisions_before_first_source']} (of {r['decisions_total']} dated) | citing "
          f"outside evidence {r['citing_outside_evidence']} (lexical proxy, upper bound) | "
          f"kills before code {r['kills_before_code']} | sessions {r['sessions']}")
    print("Unit: one build-or-kill decision, discovery layer, evidence from outside the builder,")
    print("before the first source file. The discovery-layer condition is not applied (entries")
    print("carry no scale). Nothing was sent anywhere; paste the line if you want it counted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
