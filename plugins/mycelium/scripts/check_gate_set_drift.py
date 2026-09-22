#!/usr/bin/env python3
"""Find every copy of the per-scale gate set and compare each to the machinery.

WHY THIS EXISTS (v0.241.0), AND WHY IT REPLACES THREE BESPOKE CHECKS. Over two days, FOUR
independent copies of "which theory gates apply at which scale" were found to have drifted
from `confidence-thresholds.yml`, which is what the gating machinery actually reads:

  1. `engine/theory-gates.md` Quick Reference — L1 at 7 where the machinery wants 9; "All
     gates" at L3 and "All except JTBD" at L4, both true at twelve gates and wrong at fifteen.
  2. `skills/interview/SKILL.md` — the same table again, same drift, fixed a release later.
  3. `hooks/README.md` and `engine/README.md` — a count of thirteen against fifteen defined.
  4. A CONSUMER's test harness hardcoded one twelve-gate list for every scale. Measured
     consequence: an L0 diamond was initialised with `jtbd`, which the Applicability Matrix
     marks "--" at every L0 transition, and **eight progression attempts were then correctly
     refused on a gate that should never have been there.** The framework was right; the
     instruction handed to the agent was wrong.

Each was fixed individually, each got its own parity test, and each time the next copy was
found by accident. **Fixing copies one at a time is the treadmill; discovering them is the
fix.** This scans instead of assuming, so copy five is reported the day it appears rather than
the day it misleads someone.

WHAT IT CANNOT DO. It finds ENUMERATIONS, not reasoning. A doc that describes the gate model in
prose without listing names is invisible here and can still be wrong. And it asserts agreement
with `confidence-thresholds.yml`, never that that file is correct — every copy can be wrong
together and this stays green.

EXIT: 0 clean or informational; 1 on a drifted authoritative enumeration or an undeclared new
copy; 2 when the source of truth is absent, because nothing was scanned and a green there
would be indistinguishable from a working check.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Every gate name the framework defines, in the key form `required_theory_gates` uses.
GATE_KEYS = {
    "evidence", "four_risks", "jtbd", "cynefin", "bias", "security", "privacy", "bvssh",
    "service_quality", "delivery_metrics", "corrections", "regulatory", "explainability",
    "landscape", "capacity",
}

#: Prose spellings seen in real tables, mapped to the key form.
ALIASES = {
    "four risks": "four_risks",
    "service quality": "service_quality",
    "service & usability quality": "service_quality",
    "delivery metrics": "delivery_metrics",
    "dora / delivery metrics": "delivery_metrics",
}

#: A line carrying one of these is ILLUSTRATIVE — it does not claim to be the whole set, so
#: comparing it to the machinery would produce a false positive. `feedback-loops.md` names
#: eight gates and ends "etc."; flagging that would train a reader to ignore this check.
ILLUSTRATIVE = re.compile(
    r"\betc\b|\be\.g\.|\bsuch as\b|\bfor example\b|\band more\b|…",
    re.IGNORECASE,
)

#: Files KNOWN to carry an authoritative per-scale enumeration. A file enumerating gates that
#: is NOT in here is reported as an undeclared copy: not necessarily wrong, but nobody has
#: said it should exist, and every drift so far began as a copy nobody was comparing.
DECLARED = {
    "engine/theory-gates.md",      # the Quick Reference table + per-gate Applicable-gates lines
    "skills/interview/SKILL.md",   # the second initialisation table an agent follows
    "engine/README.md",            # index prose naming the full set
    "hooks/README.md",             # gate-evaluation hook description naming the full set
}

#: Counted-but-not-enumerated claims of the form all-N-gates drift the same way and are
#: cheap to catch. The example is spelled out rather than quoted because quoting it here
#: would make this comment match its own pattern -- and exempting this file from its own
#: check would leave a hole shaped exactly like the checker.
COUNT_CLAIM = re.compile(r"\ball (\d+) gates\b", re.IGNORECASE)

SCALE_ROW = re.compile(r"^\|\s*(L[0-5])\s*\|")

#: A line must name at least this many gates to count as an enumeration. Below it, a
#: mention is prose ("the evidence and bias gates") rather than a list claiming to be a set.
#: Four is deliberately low: the smallest real gate set is L0's five, so a four-name line is
#: already close enough to a set that a reader could mistake it for one.
MIN_GATES_FOR_ENUMERATION = 4


def _normalise(token: str) -> str:
    t = token.strip().lower().strip("*`|")
    return ALIASES.get(t, t.replace(" ", "_"))


def _gates_on(line: str) -> set[str]:
    toks = {_normalise(t) for t in re.split(r"[,|]", line) if t.strip()}
    return toks & GATE_KEYS


def machinery(root: Path) -> dict[str, set[str]]:
    path = root / "plugins" / "mycelium" / "engine" / "confidence-thresholds.yml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {s: set(v["required_theory_gates"]) for s, v in doc["scales"].items()}


@dataclass
class Findings:
    """Everything one scan produced. A single object rather than seven out-parameters:
    the helper had grown past what a reader can hold, which is the same readability
    argument the complexity limit encodes."""

    authoritative: list = field(default_factory=list)
    illustrative: list = field(default_factory=list)
    counts: list = field(default_factory=list)
    files_with_gates: set = field(default_factory=set)


def _classify_lines(rel: str, text: str, total_defined: int, out: Findings) -> None:
    """Classify every line of one file. Extracted from `scan` so each function does one
    thing: `scan` decides WHICH files to read, this decides what a line IS."""
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in COUNT_CLAIM.finditer(line):
            claimed = int(m.group(1))
            if claimed != total_defined:
                out.counts.append((rel, lineno, claimed, total_defined))

        found = _gates_on(line)
        if len(found) < MIN_GATES_FOR_ENUMERATION:
            continue
        out.files_with_gates.add(rel)
        if ILLUSTRATIVE.search(line):
            out.illustrative.append((rel, lineno, sorted(found)))
            continue
        scale = SCALE_ROW.match(line.strip())
        out.authoritative.append((rel, lineno, scale.group(1) if scale else None, found))


def scan(root: Path):
    """Return (authoritative, illustrative, count_claims, undeclared_files)."""
    plugin = root / "plugins" / "mycelium"
    total_defined = len(GATE_KEYS)
    out = Findings()

    for path in sorted(plugin.rglob("*")):
        if not path.is_file() or path.suffix not in (".md", ".yml", ".yaml", ".py"):
            continue
        if "__pycache__" in str(path):
            continue
        rel = str(path.relative_to(plugin))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if rel == "engine/confidence-thresholds.yml":
            continue  # the source of truth does not compare to itself

        _classify_lines(rel, text, total_defined, out)

    illustrative_files = {rel for rel, _lineno, _g in out.illustrative}
    undeclared = sorted(
        f for f in out.files_with_gates
        if f not in DECLARED and f not in illustrative_files
    )
    return out, undeclared


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if not (root / "plugins" / "mycelium" / "engine" / "confidence-thresholds.yml").exists():
        # EXIT 2, NOT 0, and the difference is the whole point. An earlier draft printed
        # this same message and returned 0, reasoning that saying "not a pass" made it
        # honest. `test_check_empty_input_honesty.py` caught it: the MESSAGE said one thing
        # and the EXIT CODE said another, and only the exit code is read by CI, by the
        # pre-push hook, and by any script chaining on it. A check that looked at nothing
        # and returns success is indistinguishable from one that works, and reads green
        # forever. The source of truth is a precondition, so its absence is exit 2.
        print("check_gate_set_drift: PRECONDITION FAILED — no "
              "plugins/mycelium/engine/confidence-thresholds.yml under "
              f"{root}. NOTHING WAS SCANNED: no gate-set copy has been compared to anything, "
              "and no claim about drift is being made in either direction.", file=sys.stderr)
        return 2

    required = machinery(root)
    found, undeclared = scan(root)
    return _report(found, undeclared, required)


def _print_illustrative(found: Findings) -> None:
    if not found.illustrative:
        return
    print("\n  ILLUSTRATIVE — names gates but does not claim the whole set, so not compared.")
    print("  Not a pass and not a defect: an 'etc.' list is allowed to be partial.")
    for rel, lineno, names in found.illustrative:
        print(f"    {rel}:{lineno} ({len(names)} named)")


def _print_counts(found: Findings) -> list:
    if not found.counts:
        return []
    print("\n  STALE COUNT CLAIM — says 'all N gates' where N is not the number defined:")
    out = []
    for rel, lineno, claimed, actual in found.counts:
        out.append(f"    {rel}:{lineno} claims {claimed} gates; {actual} are defined")
        print(f"    {rel}:{lineno} claims {claimed}, actual {actual}")
    return out


def _print_undeclared(undeclared: list) -> list:
    if not undeclared:
        return []
    print("\n  UNDECLARED COPY — enumerates gates but is not in DECLARED. Not necessarily")
    print("  wrong; nobody has said it should exist, and every drift so far began here.")
    out = []
    for rel in undeclared:
        out.append(f"    {rel} enumerates a gate set and is not declared")
        print(f"    {rel}")
    return out


def _report(found: Findings, undeclared: list, required: dict) -> int:
    """Print the findings and decide the exit code. Split from `main` so argument
    handling and judgement are separate functions."""

    print("Per-scale gate-set copies (source of truth: confidence-thresholds.yml)")
    print("=" * 70)
    print(f"  {len(GATE_KEYS)} gates defined; {len(found.authoritative)} authoritative "
          f"enumeration(s), {len(found.illustrative)} illustrative, "
          f"{len(found.counts)} stale count claim(s)")

    failures = []
    for rel, lineno, scale, names in found.authoritative:
        if scale is None or scale not in required:
            continue
        want = required[scale]
        if names != want:
            failures.append(
                f"    {rel}:{lineno} [{scale}] has {sorted(names)}; machinery requires "
                f"{sorted(want)} (missing {sorted(want - names)}, extra {sorted(names - want)})")

    _print_illustrative(found)
    failures += _print_counts(found)
    failures += _print_undeclared(undeclared)

    if failures:
        print(f"\nFAIL: {len(failures)} problem(s).")
        for f in failures:
            print(f)
        print("\nFix the COPY, not this check. `confidence-thresholds.yml` is what the gating")
        print("machinery reads; a doc that disagrees with it misleads whoever reads the doc.")
        return 1

    print("\nOK: every authoritative enumeration agrees with the machinery.")
    print("WHAT THIS DOES NOT MEAN: that the gate model is right. It compares copies to one")
    print("source; they can all be wrong together and this stays green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
