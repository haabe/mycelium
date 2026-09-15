#!/usr/bin/env python3
"""Records against cycles, per scale: how full is the catalogue, and how many doors are open?

WHY THIS EXISTS. The framework's only instruction that creates a child diamond sits under
`diamond-progress` step 9, "If progressing", so a record became a cycle only as a
side-effect of its parent advancing. The dogfood repo measured the consequence on
2026-09-02: 73 opportunity records against 1 L2 diamond ever, 54 solution records against 0
L3 diamonds ever, both parents static for three months, and a founder's sentence for the
symptom: "it looks like how I never could get past L1 whilst the product already existed."
The register row diamond-spawning-is-reachable-only-from-a-parent-progressing proposed a
one-line diagnostic that would have surfaced this in May. This is it.

WHAT IT COUNTS. Records: L2 = opportunities in opportunities.yml; L3 = solution leaves under
them (a leaf whose status is terminal is excluded, since it is done, not waiting). Cycles:
diamonds in diamonds/active.yml by `scale`, active or parked, plus the count that ever
existed when a `completed_diamonds` or `archived_diamonds` list is present. The number is
"N records, M active cycles", and the finding fires when records exist at a scale with no
cycle ever opened at it. Nothing is opened by this script; ost-builder and ice-score carry
the exit that does (0.217.0).

Exit codes: 0 report printed; 1 NOT A PASS when there is nothing to count (no
opportunities.yml and no diamonds); 2 precondition (canvas dir missing).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

_TERMINAL = re.compile(
    r"^(shipped|launched|launch-validated|discarded|killed|archived|validated|rejected|not-built)",
    re.IGNORECASE)
_SCALE = re.compile(r"^L[0-5]$")


def _load(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def records(canvas_dir: Path) -> dict[str, int]:
    """L2 and L3 record counts from opportunities.yml (terminal solutions excluded)."""
    data = _load(canvas_dir / "opportunities.yml")
    opps = data.get("opportunities") if isinstance(data, dict) else None
    l2 = l3 = 0
    for opp in opps or []:
        if not isinstance(opp, dict):
            continue
        l2 += 1
        for sol in opp.get("solutions") or []:
            if isinstance(sol, dict) and not _TERMINAL.match(str(sol.get("status") or "")):
                l3 += 1
    return {"L2": l2, "L3": l3}


def cycles(canvas_dir: Path) -> dict[str, dict[str, int]]:
    """scale -> {'active': n, 'ever': n} from diamonds/active.yml."""
    data = _load(canvas_dir.parent / "diamonds" / "active.yml")
    out: dict[str, dict[str, int]] = {}
    if not isinstance(data, dict):
        return out
    for key, live in (("active_diamonds", True), ("parked_diamonds", True),
                      ("completed_diamonds", False), ("archived_diamonds", False)):
        for dm in data.get(key) or []:
            if not isinstance(dm, dict):
                continue
            scale = str(dm.get("scale") or dm.get("level") or "").upper()
            if not _SCALE.match(scale):
                continue
            row = out.setdefault(scale, {"active": 0, "ever": 0})
            row["ever"] += 1
            row["active"] += live
    return out


def findings(canvas_dir: Path) -> list[str]:
    rec, cyc = records(canvas_dir), cycles(canvas_dir)
    out = []
    for scale, n in rec.items():
        row = cyc.get(scale, {"active": 0, "ever": 0})
        if n and row["ever"] == 0:
            out.append(f"{scale}: {n} record(s) and no {scale} diamond has ever been opened; the "
                       f"catalogue has an intake and no outlet at this scale")
        elif n and row["active"] == 0:
            out.append(f"{scale}: {n} record(s), 0 active {scale} diamond(s) ({row['ever']} ever)")
    return out


def report(canvas_dir: Path) -> int:
    rec, cyc = records(canvas_dir), cycles(canvas_dir)
    if not rec["L2"] and not cyc:
        print("NOT A PASS: no opportunities and no diamonds; nothing to count.")
        return 1
    print("Scale occupancy (records in the catalogue against cycles of work)")
    print("=" * 70)
    for scale in ("L0", "L1", "L2", "L3", "L4", "L5"):
        row = cyc.get(scale, {"active": 0, "ever": 0})
        recs = f"{rec[scale]} record(s)" if scale in rec else "records not counted at this scale"
        print(f"  {scale}: {recs}; {row['active']} active diamond(s), {row['ever']} ever")
    hits = findings(canvas_dir)
    print()
    for h in hits:
        print(f"  FINDING {h}")
    if not hits:
        print("  Every scale with records has had a cycle opened at it.")
    print("\nA record and a cycle are different objects (engine/diamond-rules.md). A scale with")
    print("records and no cycle has an intake and no outlet; ost-builder and ice-score offer the")
    print("exit, and nothing is opened here.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    args = ap.parse_args()
    canvas = Path(args.canvas_dir)
    if not canvas.is_dir():
        print(f"scale-occupancy: not a directory: {canvas}", file=sys.stderr)
        return 2
    return report(canvas)


if __name__ == "__main__":
    raise SystemExit(main())
