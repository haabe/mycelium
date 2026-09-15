#!/usr/bin/env python3
"""Does a theory named PRIMARY for a scale appear in that scale's required gates?

WHY THIS EXISTS. `engine/diamond-rules.md` names primary theories per scale and
`engine/confidence-thresholds.yml` names `required_theory_gates` per scale. Until 0.217.0
nothing joined them, so a theory could be cited as load-bearing for a scale and enforced
nowhere at it. Found in the dogfood repo 2026-09-02 (register row
two-of-the-three-justifiers-have-no-gate-at-any-tier): Wardley Mapping and Team Topologies
were both named PRIMARY for L1 and neither was an L1 gate, and the prototype's first run
found the finding larger than the prompt: all three of L1's primary theories were ungated
at L1. The strategy scale was gated entirely by theories that were not its own.

THE MAPPING IS THE JUDGEMENT AND IT IS EXPLICIT. Theory names and gate names do not share
a vocabulary, so THEORY_TO_GATE is a hand-written table: a theory maps to a gate only where
the gate's own definition in theory-gates.md cites that theory as its source. Anything
unmapped is reported as UNMAPPED, never guessed; a wrong guess would manufacture a finding.
An entry mapped to None says "this theory has no gate at any tier", which is itself the
LANDSCAPE / CAPACITY finding the row was filed about.

WHAT AN UNGATED ROW MEANS, and what it does not. The theory is cited as primary for the
scale and does not appear in its required gates. It may still be implemented as an opt-in
skill. It is NOT a claim that the theory should become a blocking gate (opp-072 on
gate-remedy proportionality; the 0.217.0 remedy was two NUDGE-tier gates, not two blocks).

Exit codes: 0 report printed; 1 NOT A PASS when the scale table or the thresholds hold no
scales (nothing joined); 2 engine files not found.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

#: Deliberately conservative: a theory maps to a gate only where theory-gates.md cites it.
THEORY_TO_GATE: dict[str, str | None] = {
    "torres": "evidence",
    "gilad": "evidence",
    "ellis": "evidence",
    "allen": "evidence",
    "christensen": "jtbd",
    "ulwick": "jtbd",
    "jtbd": "jtbd",
    "cagan": "four_risks",
    "cynefin": "cynefin",
    "snowden": "cynefin",
    "shotton": "bias",
    "kahneman": "bias",
    "smart": "bvssh",
    "bvssh": "bvssh",
    "downe": "service_quality",
    "nielsen": "service_quality",
    "forsgren": "delivery_metrics",
    "dora": "delivery_metrics",
    "owasp": "security",
    "wardley": "landscape",          # LANDSCAPE justifier; a NUDGE-tier gate since 0.217.0
    "team topologies": "capacity",   # CAPACITY justifier; a NUDGE-tier gate since 0.217.0
    "skelton": "capacity",
    "sinek": None,                   # Golden Circle: no gate at any tier (dogfood opp-063)
    "north star": None,
    "lauchengco": None,
    "ries": None,
    "dry/kiss": None,                # engineering principles at L4: practices, not a gated theory
}
_SCALE_ROW = re.compile(r"\|\s*\*\*(L[0-5])\*\*\s*\|")
_THEORY_SPLIT = re.compile(r",(?![^(]*\))")
_MIN_CELLS = 6
_THEORY_CELL = 4


def parse_primary_theories(rules_path: Path) -> dict[str, list[str]]:
    """scale -> primary theories, from the L0-L5 table in diamond-rules.md."""
    out: dict[str, list[str]] = {}
    for line in rules_path.read_text(encoding="utf-8").splitlines():
        m = _SCALE_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < _MIN_CELLS:
            continue
        out[m.group(1)] = [t.strip() for t in _THEORY_SPLIT.split(cells[_THEORY_CELL]) if t.strip()]
    return out


def gate_for(theory: str) -> tuple[str | None, bool]:
    """(gate name or None, mapped). mapped=False means the table has no entry: not guessed."""
    low = theory.lower()
    for key, gate in THEORY_TO_GATE.items():
        if key in low:
            return gate, True
    return None, False


def join(primary: dict[str, list[str]], scales: dict) -> dict[str, list[tuple[str, str]]]:
    """{'gated': [...], 'ungated': [...], 'unmapped': [...]} of (scale, theory) pairs."""
    out: dict[str, list[tuple[str, str]]] = {"gated": [], "ungated": [], "unmapped": []}
    for scale, theories in sorted(primary.items()):
        entry = scales.get(scale) if isinstance(scales, dict) else None
        gates = set(entry.get("required_theory_gates") or []) if isinstance(entry, dict) else set()
        for t in theories:
            gate, mapped = gate_for(t)
            if not mapped:
                out["unmapped"].append((scale, t))
            elif gate is not None and gate in gates:
                out["gated"].append((scale, t))
            else:
                out["ungated"].append((scale, t))
    return out


def report(result: dict[str, list[tuple[str, str]]]) -> None:
    total = sum(len(v) for v in result.values())
    print("Primary-theory gate join (is a scale's primary theory a gate at that scale?)")
    print("=" * 74)
    print(f"  {total} primary-theory/scale pairs: {len(result['gated'])} gated, "
          f"{len(result['ungated'])} UNGATED, {len(result['unmapped'])} unmapped\n")
    for scale, t in result["ungated"]:
        print(f"  UNGATED   {scale}: {t}")
    for scale, t in result["unmapped"]:
        print(f"  unmapped  {scale}: {t}  (no entry in THEORY_TO_GATE; not guessed)")
    print("\nWHAT AN UNGATED ROW MEANS: the theory is cited as primary for that scale and does")
    print("not appear in its required_theory_gates. It may still be an opt-in skill. It is NOT")
    print("a claim that the theory should become a blocking gate (gate-remedy proportionality).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--framework-root", default=None,
                    help="plugin root holding engine/; default: this script's parent tree")
    args = ap.parse_args()
    root = Path(args.framework_root) if args.framework_root else Path(__file__).resolve().parents[1]
    rules = root / "engine" / "diamond-rules.md"
    thresholds = root / "engine" / "confidence-thresholds.yml"
    if not rules.is_file() or not thresholds.is_file():
        print(f"primary-theory-gated: engine files not found under {root}", file=sys.stderr)
        return 2
    primary = parse_primary_theories(rules)
    try:
        scales = (yaml.safe_load(thresholds.read_text(encoding="utf-8")) or {}).get("scales") or {}
    except yaml.YAMLError as exc:
        print(f"primary-theory-gated: confidence-thresholds.yml unreadable: {exc}", file=sys.stderr)
        return 2
    if not primary or not scales:
        print("NOT A PASS: no scale rows in diamond-rules.md or no scales in "
              "confidence-thresholds.yml; nothing was joined.")
        return 1
    report(join(primary, scales))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
