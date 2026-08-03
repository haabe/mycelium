#!/usr/bin/env python3
"""check_negative_control.py — every guard's test must prove the guard BITES.

WHY THIS EXISTS
---------------
Check 37 (G-V12) asks "does every check have a test?" It never asks whether that
test would FAIL if the check stopped working. Those are different questions, and
the gap between them is where the expensive bugs live:

  - `verify_citations.py` shipped with 14 passing unit tests while its matcher
    required a colon that occurs ZERO times in real agent output. It matched 0%
    of live citations for ~2.5 months and reported "no problems found" on every
    run (fixed v0.60.1).
  - The auto-dogfood battery scored 7/7 both WITH and WITHOUT the operating
    contract injected (07-17 baseline vs 07-25 post-fix). A score that does not
    move when the framework is removed is not measuring the framework.

Both are the same defect: a test whose verdict does not depend on the thing it
claims to test. A passing suite then certifies nothing, and — worse — it is
actively misleading, because green is read as evidence.

So this guard asks the one question Check 37 leaves out: for each shipped guard,
does its test corpus contain at least one assertion in the FAILURE direction —
a deliberately broken input that the guard is asserted to reject?

This is a structural check, not a mutation tester. It cannot prove the failure
assertion is meaningful; it can prove one exists, which is the difference between
"we thought about the sad path" and "we only ever tested the happy path."

Usage:
    check_negative_control.py [--root REPO_ROOT] [--json]

Exit codes:
    0 — every guard's test asserts the failure direction
    1 — at least one guard is only ever tested passing (CI gate)
    2 — argument/setup error

Python stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PLUGIN_REL = "plugins/mycelium"

# Guards: things whose job is to REJECT something. A guard tested only on input
# it accepts has an untested primary function.
GUARD_GLOBS = [
    f"{PLUGIN_REL}/scripts/check_*.py",
    f"{PLUGIN_REL}/scripts/validate_*.py",
    f"{PLUGIN_REL}/hooks/*.sh",
]

# Tokens that constitute a failure-direction assertion.
#
# Python: a non-zero exit from main(), a findings/errors list asserted non-empty,
# or an explicit rejection count.
PY_FAILURE_TOKENS = [
    r"==\s*1\b",             # main([...]) == 1
    r"==\s*2\b",             # setup-error exit
    r"!=\s*0\b",
    r"len\([^)]*\)\s*==\s*[1-9]",
    r"assert\s+(?:findings|errors|hits|report\[)",
    r"pytest\.raises",
    r"is_error",
    # PreToolUse hooks signal refusal in the stdout PAYLOAD, not the exit code —
    # test_scope_check.py's own docstring notes "both allow and deny exit 0".
    # Omitting this idiom made the guard false-positive on two hooks that DO
    # assert denial, which is why it was measured against the real test corpus
    # before being trusted (corrections.md 2026-07-19: validated-against-the-
    # wrong-corpus).
    r"permissionDecision",
    r'"deny"',
    r"emit_deny",
]
# Bash: hook contracts are exit 2 (block) or a deny decision or a FAIL line.
SH_FAILURE_TOKENS = [
    r'assert_eq\s+"\$\{?\w+\}?"\s+"[12]"',
    r'"permissionDecision":\s*"deny"',
    r"assert_contains[^\n]*(?:FAIL|deny|BLOCK|blocked)",
    r'assert_eq[^\n]*"2"',
]

# A guard can only be asked for a failure-direction assertion if it HAS a failure
# direction. Rather than hand-list the advisory hooks — the enumerate-the-scope
# anti-pattern this release exists to kill — derive it: a hook that never blocks
# (no `exit 2`, no deny decision) is a recorder or a nudge, and has nothing to
# reject. Add a blocking construct and the guard immediately owes a sad-path test,
# with no list to remember to update.
BLOCKING_RE = re.compile(r"exit\s+2\b|permissionDecision[\"']?\s*:\s*[\"']?deny")

# The one irreducible exemption: a stub with no behaviour yet in either direction.
EXEMPT = {
    "check_gated_by.py":
        "documented DRAFT stub that intentionally does nothing yet — it has no "
        "reject behaviour to assert until it graduates",
}


def _is_advisory(guard: Path) -> bool:
    """True when a hook cannot block, so it has no failure direction."""
    if guard.suffix != ".sh":
        return False
    return not BLOCKING_RE.search(guard.read_text(errors="replace"))


def _test_files_for(name: str, root: Path):
    """Every test file that plausibly covers `name`."""
    stem = Path(name).stem
    # Hook filenames are hyphenated (framework-guard.sh) while their Python
    # helpers and tests are underscored (test_framework_guard.py). Try both
    # spellings in both test trees, or the guard reads as untested when it isn't.
    variants = {stem, stem.replace("-", "_"), stem.replace("_", "-")}
    cands = [
        root / d / f"test_{v}{ext}"
        for v in variants
        for d, ext in (("tests/python", ".py"), ("tests/bash", ".sh"))
    ]
    found = [c for c in cands if c.is_file()]
    # A hook is a thin dispatcher: scope-gate.sh delegates every decision to
    # scope_check.py. The helper's test is where the sad path lives, so resolve
    # it mechanically from the hook's own source rather than by a naming guess.
    sub = "hooks" if name.endswith(".sh") else "scripts"
    guard_path = root / PLUGIN_REL / sub / name
    if guard_path.is_file():
        helpers = set(re.findall(r"([a-z_]+)\.py", guard_path.read_text(errors="replace")))
        found.extend(
            t
            for h in sorted(helpers)
            if (t := root / "tests/python" / f"test_{h}.py").is_file() and t not in found
        )
    # Hook tests are not always named after the file (e.g. discovery-gate.sh ->
    # test_discovery_gate.sh); fall back to any test naming the guard.
    if not found:
        for d in ("tests/python", "tests/bash"):
            found.extend(
                t
                for t in sorted((root / d).glob("test_*"))
                if name in t.read_text(errors="replace")
            )
    return found


def scan(root: Path):
    findings = []
    guards = []
    for g in GUARD_GLOBS:
        guards.extend(sorted(root.glob(g)))

    checked = 0
    for guard in guards:
        name = guard.name
        if name in EXEMPT or _is_advisory(guard):
            continue
        checked += 1
        tests = _test_files_for(name, root)
        if not tests:
            findings.append({
                "guard": name,
                "detail": (
                    "no test file found. Check 37 covers numbered validator "
                    "checks; a standalone guard needs tests/python/test_<name>.py "
                    "or tests/bash/test_<name>.sh."
                ),
            })
            continue

        # UNION, not either/or: a hook is a .sh file whose sad path is often
        # asserted in a PYTHON test of its helper (scope-gate.sh -> scope_check.py).
        # Selecting the token set by the GUARD's extension checked a Python test
        # file with bash idioms and false-positived on a hook that does assert
        # denial. The two sets are complementary, so use both.
        tokens = PY_FAILURE_TOKENS + SH_FAILURE_TOKENS
        corpus = "\n".join(p.read_text(errors="replace") for p in tests)
        if not any(re.search(t, corpus) for t in tokens):
            findings.append({
                "guard": name,
                "detail": (
                    "its test corpus ("
                    + ", ".join(str(p.relative_to(root)) for p in tests)
                    + ") contains no failure-direction assertion. Add a case "
                    "that feeds deliberately broken input and asserts the guard "
                    "REJECTS it — otherwise a guard that stops working keeps "
                    "passing its own tests (the verify_citations failure mode)."
                ),
            })

    return {"guards_checked": checked, "findings": findings}


#: A check that CANNOT apply to a repo is a different state from one that
#: applies and found nothing, and v0.74.0/v0.75.0 collapsed the two. Running
#: these in a plugin CONSUMER repo — which has no `plugins/mycelium/` tree at
#: all — produced NOT A PASS on something the user can do nothing about. False
#: alarms are how a check gets ignored, which is the same failure this guard
#: family exists to prevent, arriving from the other side.
#:
#:   precondition ABSENT  -> N/A, exit 0, say which repo kind it is for
#:   precondition PRESENT, population empty -> refuse, exit 1

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Require every guard's tests to assert the failure direction.",
    )
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    # scripts live at <root>/plugins/mycelium/scripts/
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    if not (root / PLUGIN_REL).is_dir():
        print(f"Negative control: N/A — no {PLUGIN_REL}/ tree under {root}. This "
              "check guards the FRAMEWORK repo's own blocking guards; a plugin "
              "consumer ships none. Nothing was checked, and nothing was "
              "supposed to be.")
        return 0

    report = scan(root)
    findings = report["findings"]

    # Verdict decided BEFORE the output branch (code review 2026-08-03): the
    # refuse-on-empty branch lived inside the `else` of `if args.json:`, so the
    # machine-readable path still exited 0 over an empty population.
    rc = 1 if (report["findings"] or not report["guards_checked"]) else 0

    if args.json:
        print(json.dumps({**report, "verdict": "fail" if rc else "pass"}, indent=2))
        return rc
    print(f"Negative control: {report['guards_checked']} guard(s) checked for a "
          f"failure-direction assertion (advisory/non-blocking hooks derived, "
          f"not listed; {len(EXEMPT)} stub exempt).")
    if findings:
        print(f"\nGUARDS TESTED ONLY PASSING ({len(findings)}):")
        for f in findings:
            print(f"  {f['guard']}\n      {f['detail']}")
        print("\nA test that cannot fail certifies nothing, and green is read "
              "as evidence.")
    elif not report["guards_checked"]:
        # Refuse the universal over an empty set. "Every guard asserts its
        # own failure direction" is vacuously true across zero guards, and a
        # reader takes it as coverage. Found 2026-08-02 while assessing the
        # CALMS Automation bar this line is an instance of.
        print("NOT A PASS: 0 guards were checked, so nothing was verified. "
              "Either this project ships no blocking guards yet, or the "
              "derivation has stopped recognising the ones it has.")
        return 1
    else:
        print(f"Every one of the {report['guards_checked']} checked guard(s) "
              "asserts its own failure direction. Guards not derived as "
              "blocking are outside this count.")

    return 1 if findings else 0

    return rc


if __name__ == "__main__":
    sys.exit(main())
