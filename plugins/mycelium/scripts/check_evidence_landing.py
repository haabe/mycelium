#!/usr/bin/env python3
"""check_evidence_landing.py — gathered evidence must land on a canvas entry that cites it back.

THE QUADRANT THIS CLOSES. `check_evidence_landed.py` covers one case: a CLOSED task whose
`canvas_refs` declared a destination its findings never reached. This check covers every source
that carries evidence, whatever its state: human tasks with inbound touches or findings, assumption-
test and report files, user needs. Either a reader canvas cites the source, or the source is an
ORPHAN. Measured on the dogfood canvas that motivated it (2026-09-06): a three-reader coverage
sweep found 49 of 98 human tasks cited nowhere in opportunities.yml, and the strongest replicated
result in the corpus not on the opportunity that states that need. Nothing had measured it,
because `/log-evidence` writes `evidence_logged_to` on the task and nothing checked that the
target cites the task back. Adopted there as a dogfood-local script; 63 orphans at adoption, 0
three days later.

THE INVARIANT, in five classes, reported per source:
  LANDED              a reader canvas file names the source (its id or filename).
  CLAIMED_NOT_LANDED  the task carries `evidence_logged_to` but no reader names the task id.
                      The sharpest class: a write that reported success.
  ORPHAN              the source carries evidence (an inbound touch, partial_findings, key_finding,
                      a reply field, or is a file in a source dir) and no reader names it.
  NO_EVIDENCE         a task with no evidence signal and no citation. Fine. Not counted.
  REVIEWED            listed in `.claude/harness/evidence-landing-ledger.yml` with a reason
                      (produced nothing citable, superseded, duplicate). Reported, never failed.

WHY IT FAILS ONLY ON REGRESSION. A brownfield canvas has a backlog nobody can clear in an afternoon,
and a red gate on a number that cannot move trains dismissal. `--write-baseline` records the current
orphan set to `.claude/evals/evidence-landing-baseline.json`; the check fails only on a source that
is not in it. The baseline is meant to shrink and never to grow; the run prints how much of it has
landed since adoption so the number is watched rather than merely stored.

WHAT IT DELIBERATELY DOES NOT DO. It does not judge whether a citation is the RIGHT one, only that a
reader names the source; a task cited for one finding may hold three uncited ones, and that needs a
reader, not a grep. It cannot see evidence in prose fields it does not scan (EVIDENCE_KEYS lists the
fields log-evidence and outreach tasks actually use).

PRECONDITION UNMET SPEAKS. No `.claude/canvas` in the project: prints N/A and exits 0, so a fresh
project is told rather than failed, and a silent exit is never mistaken for "checked and clean".

Exit 0 clean or N/A; 1 on regression (a new ORPHAN or CLAIMED_NOT_LANDED) or on any
CLAIMED_NOT_LANDED not in the baseline; 2 on a usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

READER_FILES = ("opportunities.yml", "purpose.yml", "scenarios.yml", "user-needs.yml",
                "jobs-to-be-done.yml", "go-to-market.yml", "landscape.yml", "north-star.yml")
DEFAULT_SOURCE_DIRS = (".claude/evals/assumption-tests", ".claude/evals/dogfood-reports")
EVIDENCE_KEYS = ("partial_findings", "key_finding", "key_findings", "evidence_logged_to")
EVIDENCE_KEY_PREFIXES = ("reply", "replies_read", "inbound", "verbatim")
CLASSES = ("LANDED", "CLAIMED_NOT_LANDED", "ORPHAN", "NO_EVIDENCE", "REVIEWED")


def load_yaml(p: Path):
    try:
        return yaml.safe_load(p.read_text()) or {}
    except Exception as e:  # noqa: BLE001
        # speaks: an unreadable file is reported, never treated as empty-and-clean
        print(f"evidence-landing: cannot parse {p}: {e}")
        return {}


def has_evidence(task: dict) -> bool:
    for k, v in task.items():
        if k in EVIDENCE_KEYS and v:
            return True
        if any(str(k).lower().startswith(pfx) for pfx in EVIDENCE_KEY_PREFIXES) and v:
            return True
    for e in task.get("touch_log") or []:
        if isinstance(e, dict) and str(e.get("direction", "")).lower() == "inbound":
            return True
    return False


class Landing:
    def __init__(self, root: Path):
        self.root = root
        self.canvas = root / ".claude" / "canvas"
        self.readers = [self.canvas / f for f in READER_FILES]
        self.readers.append(root / ".claude" / "diamonds" / "active.yml")
        self.human_tasks = self.canvas / "human-tasks.yml"
        self.user_needs = self.canvas / "user-needs.yml"
        self.ledger_path = root / ".claude" / "harness" / "evidence-landing-ledger.yml"
        self.baseline_path = root / ".claude" / "evals" / "evidence-landing-baseline.json"
        self.ledger: dict[str, str] = {}
        self.source_dirs = [root / d for d in DEFAULT_SOURCE_DIRS]
        if self.ledger_path.exists():
            doc = load_yaml(self.ledger_path)
            for e in doc.get("reviewed") or []:
                if isinstance(e, dict) and "source" in e:
                    self.ledger[str(e["source"])] = str(e.get("reason", ""))
            for d in doc.get("source_dirs") or []:
                self.source_dirs.append(root / str(d))

    def reader_text(self) -> dict[str, str]:
        return {p.name: p.read_text() for p in self.readers if p.exists()}

    def classify_tasks(self, readers: dict[str, str]) -> list[dict]:
        rows = []
        if not self.human_tasks.exists():
            return rows
        doc = load_yaml(self.human_tasks)
        for list_name, items in doc.items():
            if not isinstance(items, list):
                continue
            for t in items:
                if not isinstance(t, dict) or "id" not in t:
                    continue
                tid = str(t["id"])
                pat = re.compile(r"\b" + re.escape(tid) + r"\b")
                cited_in = [name for name, text in readers.items() if pat.search(text)]
                claim = t.get("evidence_logged_to")
                if tid in self.ledger:
                    cls = "REVIEWED"
                elif cited_in:
                    cls = "LANDED"
                elif claim:
                    cls = "CLAIMED_NOT_LANDED"
                elif has_evidence(t):
                    cls = "ORPHAN"
                else:
                    cls = "NO_EVIDENCE"
                rows.append({"source": tid, "kind": "task", "list": list_name, "class": cls,
                             "cited_in": cited_in, "claim": str(claim)[:80] if claim else None})
        return rows

    def classify_files(self, readers: dict[str, str]) -> list[dict]:
        rows = []
        alltext = "\n".join(readers.values())
        for d in self.source_dirs:
            if not d.exists():
                continue
            for p in sorted(d.glob("*.md")):
                key = p.stem
                if key in self.ledger:
                    cls = "REVIEWED"
                elif key in alltext or p.name in alltext:
                    cls = "LANDED"
                else:
                    cls = "ORPHAN"
                rows.append({"source": key, "kind": "file", "list": d.name, "class": cls,
                             "cited_in": [], "claim": None})
        return rows

    def classify_needs(self, readers: dict[str, str]) -> list[dict]:
        rows = []
        if not self.user_needs.exists():
            return rows
        doc = load_yaml(self.user_needs)
        opp_text = readers.get("opportunities.yml", "")
        for n in doc.get("needs") or doc.get("user_needs") or []:
            if not isinstance(n, dict) or "id" not in n:
                continue
            nid = str(n["id"])
            if nid in self.ledger:
                cls = "REVIEWED"
            elif re.search(r"\b" + re.escape(nid) + r"\b", opp_text):
                cls = "LANDED"
            else:
                cls = "ORPHAN"
            rows.append({"source": nid, "kind": "need", "list": "user-needs", "class": cls,
                         "cited_in": [], "claim": None})
        return rows

    def rows(self) -> list[dict]:
        readers = self.reader_text()
        return (self.classify_tasks(readers) + self.classify_files(readers)
                + self.classify_needs(readers))


def _report(rows: list[dict], base: dict, new_orphans: list[str], new_claimed: list[str],
            verbose: bool) -> int:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    summary = ", ".join(f"{k} {counts.get(k, 0)}" for k in CLASSES)
    print(f"evidence landing: {len(rows)} source(s): {summary}")
    if verbose or new_orphans or new_claimed:
        for r in rows:
            if r["class"] in ("ORPHAN", "CLAIMED_NOT_LANDED"):
                mark = "NEW " if r["source"] in new_orphans + new_claimed else "    "
                tail = f"  -> {r['claim']}" if r["claim"] else ""
                print(f"  {mark}{r['class']:19} {r['kind']:4} {r['list']:22} {r['source']}{tail}")
    if new_claimed:
        print(f"FAIL: {len(new_claimed)} source(s) claim a landing that does not cite them back: "
              + ", ".join(new_claimed))
    if new_orphans:
        print(f"FAIL: {len(new_orphans)} new orphan source(s) since baseline: "
              + ", ".join(new_orphans))
    if new_claimed or new_orphans:
        print("  Cite the source on the entry it evidences (or add it to the ledger with a reason),"
              " then re-run. First run on a canvas with a backlog: --write-baseline records it,"
              " and the gate then holds the line.")
        return 1
    orphans_now = {r["source"] for r in rows if r["class"] == "ORPHAN"}
    base_orphans = base.get("orphan", [])
    still = [x for x in base_orphans if x in orphans_now]
    landed_since = [x for x in base_orphans if x not in orphans_now]
    print(f"  baseline: {len(base_orphans)} orphan(s) at adoption, {len(still)} still to land, "
          f"{len(landed_since)} landed since; regressions: none")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="evidence that was gathered must land on a canvas entry that cites it back")
    ap.add_argument("--project-dir", type=Path, default=Path("."),
                    help="project root holding .claude/ (default: cwd)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current orphan set as the baseline")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    root = args.project_dir.resolve()
    if not (root / ".claude" / "canvas").is_dir():
        print(f"evidence-landing: N/A — no .claude/canvas under {root}; nothing was checked")
        return 0

    landing = Landing(root)
    rows = landing.rows()
    orphans = sorted(r["source"] for r in rows if r["class"] == "ORPHAN")
    claimed = sorted(r["source"] for r in rows if r["class"] == "CLAIMED_NOT_LANDED")

    if args.write_baseline:
        landing.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        landing.baseline_path.write_text(json.dumps({
            "orphan": orphans, "claimed_not_landed": claimed,
            "note": "Baseline of sources known uncited at adoption. "
                    "Meant to shrink; never to grow.",
        }, indent=1) + "\n")
        print(f"evidence-landing: baseline written with {len(orphans)} orphan and "
              f"{len(claimed)} claimed-not-landed source(s)")
    if landing.baseline_path.exists():
        base = json.loads(landing.baseline_path.read_text())
    else:
        base = {"orphan": [], "claimed_not_landed": []}
    new_orphans = [s for s in orphans if s not in base.get("orphan", [])]
    new_claimed = [s for s in claimed if s not in base.get("claimed_not_landed", [])]
    return _report(rows, base, new_orphans, new_claimed, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
