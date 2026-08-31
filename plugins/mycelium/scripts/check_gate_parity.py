#!/usr/bin/env python3
"""check_gate_parity.py — a gate that runs in CI must also run before the push.

THE DEFECT, MEASURED
--------------------
On 2026-08-09 the framework's CI workflow invoked **11** `check_*.py` gates and
the shipped pre-push hook ran **4**. Seven gates existed only in CI, which means
seven classes of defect could only ever be discovered *after* a push, as a red
build with the author already onto something else.

This is not a new lesson. `corrections.md` 2026-06-18 records it under
"Local validation != CI gates", after `check_legacy_paths.py` shipped CI-only
and two later commits went red on CI while passing every local check. That
entry's own prevention rule reads:

    When adding a CI-only gate, add it to the pre-push hook OR document the
    run-locally step in the same commit.

The rule was applied to the gate that motivated it, and to none of the seven
that came after. **A rule that depends on an author remembering it is a rule
with a decay rate.**

WHY A PARITY CHECK RATHER THAN "ADD THE SEVEN"
----------------------------------------------
Adding the seven fixes today's list and leaves tomorrow's. The lists diverge
because there are two of them, hand-maintained, in different files, edited by
different tasks — CI steps get added when a gate is written, hook lines get
added when someone remembers. So the fix is one declared list
(`local-gate-set.txt`) plus this check asserting CI never gains a gate the list
has not got.

WHAT IT DOES NOT CHECK, STATED SO THE GREEN IS NOT READ AS WIDER
-----------------------------------------------------------------
1. It compares CI against the SHIPPED gate set. It cannot see the hook actually
   installed at `.git/hooks/pre-push` in any given clone — that file is not
   version-controlled and not readable from a workflow. The hook carries its own
   self-drift warning for that half; this check owns the authoring-time half.
   (The two halves are genuinely different: this one catches "a gate was added
   to CI and not to the set"; the hook's catches "your installed copy is old".)
2. It does not verify that a gate in the set actually PASSES, or that the hook
   runs it correctly. It checks membership, not behaviour.
3. Parity is one-directional by design: the set may contain gates CI does not
   run (a slow or environment-specific check is fine to run locally only). The
   failure that costs something is CI-only, not local-only.

EXIT CODES, and they follow the shipped convention rather than a local one:
  0  parity holds
  1  REFUSE — a CI gate is missing from the set, or the workflow exists and no
     invocation matched it (input present, nothing verified)
  2  PRECONDITION — not a framework tree; the files to compare do not exist

**The first version returned 0 for the not-a-framework-tree case**, on the
reasoning that "N/A is honest". `check_empty_input_honesty.py` rejected it on the
first run of the local gate set: a check that looked at nothing and exits 0 is
indistinguishable from one that works, and reads green forever. `check_theory_fidelity.py`
already had the right answer (exit 2) and this now matches it. The guard caught
the defect in the guard, which is the entire argument for running the set locally.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WORKFLOW_REL = ".github/workflows/validate.yml"
GATE_SET_REL = "plugins/mycelium/scripts/local-gate-set.txt"

#: A gate INVOCATION in the workflow, not a mention of one. The distinction is
#: load-bearing: `validate.yml` names `check_source_independence.py` inside a
#: comment explaining what a field feeds, and that script is invoked by the
#: canvas-health SKILL rather than by CI. Counting the comment would have
#: manufactured a missing-gate finding about a check that is correctly wired
#: somewhere else — a false positive on the first real run, which is how a guard
#: earns a permanent exclusion list instead of trust.
#:
#: DIGITS ARE IN THE CHARACTER CLASS DELIBERATELY. The first version matched
#: `check_[a-z_]+` because every script in the tree today is letters-only, and a
#: test using `check_thing_0.py` exposed that a gate named with a digit would be
#: INVISIBLE here — the check would report N/A ("nothing matched") rather than a
#: missing gate, which is the quiet direction to be wrong in. Widened rather than
#: renaming the fixture, because the fixture was right and the pattern was
#: narrower than the thing it claims to scan.
INVOCATION_RE = re.compile(
    r"^\s*(?:-\s*)?(?:run:\s*)?.*python3?\s+\S*scripts/(check_[a-z0-9_]+\.py)",
    re.MULTILINE,
)

WAIVER_RE = re.compile(r"^!waived\s+(check_[a-z0-9_]+\.py)\s+(.+?)\s*$")

#: Group index of the trailing-arguments capture. Both invocation patterns capture the
#: script name first and its arguments second; a pattern with only the name has no group 2.
_ARGS_GROUP = 2


#: The same line as INVOCATION_RE, but keeping what follows the script name so flags can be
#: compared. Name-only parity was not enough: see strict_mismatches.
INVOCATION_WITH_ARGS_RE = re.compile(
    r"^\s*(?:-\s*)?(?:run:\s*)?.*python3?\s+\S*scripts/(check_[a-z0-9_]+\.py)(.*)$",
    re.MULTILINE,
)


def _strict_flags(lines, pattern) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for line in lines:
        if line.lstrip().startswith("#"):
            continue
        m = pattern.match(line)
        if m:
            name = m.group(1)
            args = (m.group(_ARGS_GROUP)
                    if m.lastindex and m.lastindex >= _ARGS_GROUP else "")
            out[name] = out.get(name, False) or ("--strict" in args)
    return out


def strict_mismatches(workflow_text: str, gate_set_text: str) -> list[str]:
    """Gates CI runs with --strict that the local set does not, and vice versa.

    WHY THIS EXISTS (2026-08-31, v0.153.0). CI went red twice on `check_fail_open.py` while the
    pre-push hook passed every time. Both places ran the gate; CI ran it `--strict` and the
    local set ran it bare, so the SAME gate was advisory locally and blocking in CI. Name-only
    parity reported OK throughout.

    That is the 2026-08-09 drift wearing a disguise. The original failure was 11 CI gates
    against 4 local — a MISSING gate. This one is a gate with DIFFERENT TEETH in the two
    places, which is invisible to a check that compares names and produces the same outcome:
    a class of defect that can only ever go red after a push.
    """
    ci = _strict_flags(workflow_text.splitlines(), INVOCATION_WITH_ARGS_RE)
    local_re = re.compile(r"^(check_[a-z0-9_]+\.py)(.*)$")
    local = _strict_flags([ln.strip() for ln in gate_set_text.splitlines()], local_re)
    out = []
    for name, ci_strict in sorted(ci.items()):
        if name not in local:
            continue  # a missing gate is the name-parity check's business, not this one
        if ci_strict and not local[name]:
            out.append(f"{name}: CI runs it --strict, the local set does not — advisory "
                       f"locally, blocking in CI, so it can only go red after a push")
        elif local[name] and not ci_strict:
            out.append(f"{name}: the local set runs it --strict, CI does not — a push can be "
                       f"blocked locally by a gate CI would have let through")
    return out


def ci_gates(workflow_text: str) -> list[str]:
    """Gate scripts actually invoked by the workflow, in file order."""
    seen: dict[str, None] = {}
    for line in workflow_text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue  # a commented-out step is not a gate that runs
        m = INVOCATION_RE.match(line)
        if m:
            seen.setdefault(m.group(1), None)
    return list(seen)


def parse_gate_set(text: str) -> tuple[list[str], dict[str, str]]:
    """(gates, waivers) from the declared set. Waivers carry their reason."""
    gates: list[str] = []
    waivers: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        waived = WAIVER_RE.match(line)
        if waived:
            waivers[waived.group(1)] = waived.group(2)
            continue
        gates.append(line.split()[0])
    return gates, waivers


def evaluate(root: Path) -> dict:
    workflow = root / WORKFLOW_REL
    gate_set = root / GATE_SET_REL

    missing_files = [
        rel
        for rel, path in ((WORKFLOW_REL, workflow), (GATE_SET_REL, gate_set))
        if not path.is_file()
    ]
    if missing_files:
        # Honest N/A, not a pass. A consumer project has neither file, and
        # reporting "parity holds" over two absent files is the empty-input
        # dishonesty this project audits elsewhere.
        return {
            "status": "precondition",
            "detail": (
                f"not a framework tree — missing {', '.join(missing_files)}. "
                "Nothing was compared, so nothing is asserted."
            ),
        }

    workflow_text = workflow.read_text(encoding="utf-8", errors="replace")
    gate_set_text = gate_set.read_text(encoding="utf-8", errors="replace")
    ci = ci_gates(workflow_text)
    declared, waivers = parse_gate_set(gate_set_text)

    if not ci:
        return {
            "status": "refuse",
            "detail": (
                f"no gate invocations matched in {WORKFLOW_REL}. Either the workflow "
                "stopped invoking checks or the pattern no longer matches it — "
                "either way this run verified nothing."
            ),
        }

    missing = [g for g in ci if g not in declared and g not in waivers]
    return {
        "status": "fail" if missing else "ok",
        "ci_count": len(ci),
        "declared_count": len(declared),
        "waived": waivers,
        # Same gates, different teeth. Computed here so callers and tests can read it
        # without re-opening the two files. See strict_mismatches for why it exists.
        "strict_mismatches": strict_mismatches(workflow_text, gate_set_text),
        "missing": missing,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args(argv)
    result = evaluate(Path(args.root).resolve())

    if result["status"] == "precondition":
        print(f"error: {result['detail']}", file=sys.stderr)
        return 2

    if result["status"] == "refuse":
        print(f"NOT A PASS: {result['detail']}", file=sys.stderr)
        return 1

    if result["status"] == "ok":
        waived = result["waived"]
        extra = f", {len(waived)} waived" if waived else ""
        print(
            f"Gate parity: OK — all {result['ci_count']} CI gate(s) are in the "
            f"local set ({result['declared_count']} declared{extra})."
        )
        for name, reason in waived.items():
            print(f"  waived: {name} — {reason}")
        # NAME PARITY IS NOT ENOUGH, and this is checked AFTER the ok branch's own message so
        # the two findings are never confused: every gate can be present in both places and
        # still have different teeth. See strict_mismatches.
        mismatches = result.get("strict_mismatches") or []
        if mismatches:
            print("\nGate parity FAILED on FLAGS — same gates, different teeth:")
            for line in mismatches:
                print(f"  {line}")
            print("  Name parity passed. That is the point: a gate present in both places and\n"
                  "  advisory in one of them produces exactly the outcome name-parity exists to\n"
                  "  prevent — a defect class that can only go red after a push.")
            return 1
        return 0

    print(
        f"Gate parity FAILED — {len(result['missing'])} gate(s) run in CI and "
        f"nowhere before the push:",
        file=sys.stderr,
    )
    for name in result["missing"]:
        print(f"  {name}", file=sys.stderr)
    print(
        "\nA CI-only gate can only ever go red AFTER a push, with the author "
        "already onto something else.\n"
        f"Add each to {GATE_SET_REL}, or waive it there with a reason:\n"
        "  !waived <script> <why it cannot run locally>",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
