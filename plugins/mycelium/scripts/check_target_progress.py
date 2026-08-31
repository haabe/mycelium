#!/usr/bin/env python3
"""A target with nothing comparing an actual against it measures nothing.

THE GAP THIS CLOSES (founder ruling 2026-08-31: "target_value: wire it"). The canvas has
carried `target_value` beside `current_value` since north-star.yml was written. NOTHING HAS
EVER COMPARED THEM: measured that day, no script or hook read either field. The two halves
of a measurement sat adjacent in the same object, and the gap between them — the only thing
either field exists to express — was never computed by anything.

That is the defect class this release series is about, in its purest form. A `kill_criterion`
with no reader can at least be read by a human scanning the file. A target beside an actual
LOOKS like a measurement, and reads as one, while no comparison is happening anywhere.

THE THREE STATES, and the middle one is the finding:

  MEASURED   both numeric — report the gap and the percentage of target reached.
  UNMEASURED `target_value` set, `current_value` null. THE TARGET EXISTS AND NOTHING HAS
             EVER BEEN MEASURED AGAINST IT. This is a target that cannot fail, which is the
             same shape as a prediction that can never be overdue.
  N/A        target or current is prose or a mapping (e.g. "100 (3-year, Gilad's band...)").
             Skipped, and SAID OUT LOUD with the reason, never silently dropped — a skip
             nobody sees is how a check comes to cover a fraction of its population while
             reporting clean.

REPORT-ONLY unless --strict. The canvas legitimately holds aspirational targets that have
not been measured yet, and failing a build over one would teach people to delete the target
rather than measure it — the exact inversion the field exists to prevent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

#: Depth ceiling walking a canvas. Finite so pathological nesting cannot hang the gate.
_MAX_DEPTH = 12


def _numeric(value):
    """A value we can actually subtract. bool is excluded: True is not a measurement."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _label(node: dict, fallback: str) -> str:
    for key in ("id", "name", "metric"):
        val = node.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:60]
    return fallback


def classify(node: dict, canvas: str) -> tuple[str, tuple[str, str, str]]:
    """Which of the three states this target is in, and the line to print for it."""
    target = node.get("target_value")
    current = node.get("current_value")
    label = _label(node, "<unnamed>")
    t_num, c_num = _numeric(target), _numeric(current)
    if target is None:
        return "na", (canvas, label, "no target set — nothing to compare against")
    if t_num is not None and c_num is not None:
        pct = (c_num / t_num * 100) if t_num else 0.0
        return "measured", (canvas, label, f"{c_num:g} of {t_num:g} ({pct:.0f}%)")
    if t_num is not None and current is None:
        return "unmeasured", (canvas, label, f"target {t_num:g}, current_value is null")
    detail = (f"target/current not numeric ({type(target).__name__}"
              f"/{type(current).__name__}) — cannot be subtracted")
    return "na", (canvas, label, detail)


def scan(canvas_dir: Path):
    """Return (measured, unmeasured, not_applicable) triples of (canvas, label, detail)."""
    measured, unmeasured, na = [], [], []

    def walk(node, canvas: str, depth: int = 0):
        if depth > _MAX_DEPTH:
            return
        if isinstance(node, dict):
            if "target_value" in node:
                bucket, row = classify(node, canvas)
                {"measured": measured, "unmeasured": unmeasured, "na": na}[bucket].append(row)
            for val in node.values():
                walk(val, canvas, depth + 1)
        elif isinstance(node, list):
            for val in node:
                walk(val, canvas, depth + 1)

    for path in sorted(canvas_dir.glob("*.yml")):
        try:
            walk(yaml.safe_load(path.read_text()), path.stem)
        except (yaml.YAMLError, OSError):
            continue  # parse failures belong to validate_canvas
    return measured, unmeasured, na


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--canvas-dir", default=".claude/canvas")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when a target has never been measured against")
    args = ap.parse_args()

    canvas_dir = Path(args.canvas_dir)
    if not canvas_dir.is_dir():
        print(f"target-progress: NOT A PASS — no canvas dir at {canvas_dir}. Nothing checked.")
        return 1
    measured, unmeasured, na = scan(canvas_dir)
    total = len(measured) + len(unmeasured) + len(na)
    if total == 0:
        print("target-progress: NOT A PASS — no `target_value` found anywhere. Nothing was "
              "compared, which is not the same as everything being on target.")
        return 1

    print("Target progress (is anything comparing an actual against the target?)")
    print("=" * 68)
    print(f"  {total} target(s): {len(measured)} measured, {len(unmeasured)} never measured, "
          f"{len(na)} not comparable")
    for canvas, label, detail in measured:
        print(f"  MEASURED   [{canvas}] {label}: {detail}")
    for canvas, label, detail in unmeasured:
        print(f"  UNMEASURED [{canvas}] {label}: {detail}")
    for canvas, label, detail in na:
        print(f"  n/a        [{canvas}] {label}: {detail}")
    if unmeasured:
        print("\n  A TARGET NOTHING IS MEASURED AGAINST CANNOT FAIL, and a bar that cannot fail\n"
              "  is not a bar. Either measure it, or say in the entry why it is aspirational.")
    return 1 if (args.strict and unmeasured) else 0


if __name__ == "__main__":
    sys.exit(main())
