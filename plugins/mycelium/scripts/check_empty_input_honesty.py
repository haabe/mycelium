#!/usr/bin/env python3
"""Guard: no shipped check may report success over an empty population.

THE CLASS THIS CLOSES. `verify_citations.py` shipped requiring a colon in
`(per: X)`. That form occurs zero times in real output, so for roughly three
months the check ran on every push, matched nothing, and reported no problems.
Its coverage proof asserted that it EXECUTES, never that it MATCHES anything —
and no test could have caught it, because every test fed it the form it wanted.

That put CALMS Automation at amber on 2026-07-25, with the green bar written as
"a mechanism that verifies a shipped check matches live input, not merely that
it executes." v0.74.0 fixed four such checks by hand. Fixing four is not the bar;
nothing stopped the fifth. This is the fifth-stopper.

HOW IT WORKS, AND WHY IT IS NOT A PATTERN MATCH. It RUNS every shipped check
against a genuinely empty repository and reads the exit code. Grepping the source
for a refusal string would be the same mistake one level up: a comment, a
docstring, or an unreachable branch would satisfy it. Behaviour cannot be faked
by prose about behaviour.

THE RULE. On empty input a check must NOT exit 0. It may:
  * refuse            (exit 1) — "NOT A PASS: nothing was verified"
  * fail a precondition (exit 2) — "error: missing docs/theories.md"
Both are honest. Exit 0 means "I looked at nothing and everything is fine",
which is the only answer that is never true.

WHAT THIS DOES NOT CATCH, stated so a pass is not read as more than it is: a
check whose patterns match a REDUCED population rather than an empty one. A
check finding 3 of 300 live citations exits 0 here and is still broken. Empty is
the tractable end of the problem, not the whole of it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_REL = "plugins/mycelium/scripts"

#: Scripts that are not checks, or cannot be pointed at an arbitrary tree.
#: Every entry states a reason, and every reason is verifiable from the file.
EXEMPT = {
    "check_empty_input_honesty.py":
        "this guard — it obeys its own rule below rather than exempting itself",
    "check_gated_by.py":
        "self-declared DRAFT stub, verified below by reading the file",
    "check_coverage_floor.py":
        "reads a coverage json produced by a test run, not a tree; exits 2 "
        "without one, which is already honest",
    "check_bvssh_reconcile.py":
        "DELIBERATE empty-pass, documented at its own line 33: it detects "
        "ORPHANED assessments, so zero assessments means zero orphans. That is "
        "a true and useful pass, and flagging it would fail every project that "
        "has simply never run /bvssh-check. Its own test suite asserts this.",
    "verify_citations.py":
        "ADVISORY BY DESIGN — main() returns None, so it can never exit "
        "non-zero, and its own output says 'unverified != fabricated'. It "
        "cannot be judged by exit code. NAME THIS RATHER THAN FILE IT: "
        "verify_citations is the script whose 3-month blindness set the CALMS "
        "Automation bar this guard exists to serve, and it sits structurally "
        "outside the guard because advisory tools cannot fail. The bar cannot "
        "fully close for advisory reporters, and pretending otherwise by "
        "forcing an exit contract on one would be theatre.",
}

#: How to aim a script at a tree when it does not take `--root`. EXEMPT is checked
#: first, so a name in both places would make its AIM entry dead code — one was
#: written that way and removed rather than left as a misleading record.
#: Extending this turned an "untestable" skip into a real check, and it found
#: `validate_canvas.py` printing PASS over an empty directory, which is the
#: most-read green line in the framework.
AIM = {
    "validate_canvas.py": lambda empty: [str(empty / ".claude" / "canvas")],
}

#: The exemption for a stub is only valid while the file still says it is one.
STUB_MARKER = "DRAFT stub. Not yet implemented."


def _candidates(scripts_dir: Path) -> list[Path]:
    named = sorted(scripts_dir.glob("check_*.py"))
    for extra in ("validate_canvas.py", "verify_citations.py"):
        p = scripts_dir / extra
        if p.is_file():
            named.append(p)
    return named


def _accepts_root(script: Path) -> bool:
    """A check we cannot aim at an empty tree cannot be tested this way."""
    return '"--root"' in script.read_text(errors="replace") or \
           "'--root'" in script.read_text(errors="replace")


def scan(root: Path) -> dict:
    scripts_dir = root / SCRIPTS_REL
    findings: list[dict] = []
    checked: list[str] = []
    skipped: list[dict] = []

    if not scripts_dir.is_dir():
        return {"findings": findings, "checked": checked, "skipped": skipped}

    with tempfile.TemporaryDirectory(prefix="mycelium-empty-") as tmp:
        empty = Path(tmp)
        (empty / ".claude" / "canvas").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=empty, check=False,
                       capture_output=True)

        for script in _candidates(scripts_dir):
            name = script.name
            if name in EXEMPT:
                reason = EXEMPT[name]
                if name == "check_gated_by.py" and \
                        STUB_MARKER not in script.read_text(errors="replace"):
                    findings.append({
                        "script": name,
                        "detail": (
                            "exempt as a DRAFT stub, but the file no longer says "
                            f"'{STUB_MARKER}'. If it graduated into a real check "
                            "it must obey the rule; remove it from EXEMPT."
                        ),
                    })
                else:
                    skipped.append({"script": name, "reason": reason})
                continue

            extra = AIM.get(name)
            if extra is None and not _accepts_root(script):
                skipped.append({
                    "script": name,
                    "reason": ("takes no --root, so it cannot be aimed at an "
                               "empty tree. NOT a clean skip — it is untestable "
                               "by this guard and its empty-input behaviour is "
                               "unknown."),
                })
                continue

            try:
                argv = extra(empty) if extra else ["--root", "."]
                proc = subprocess.run(
                    [sys.executable, str(script), *argv],
                    cwd=empty, capture_output=True, text=True, timeout=60,
                    check=False,   # a non-zero exit is the PASS condition here
                )
            except subprocess.SubprocessError as exc:
                findings.append({"script": name,
                                 "detail": f"could not be run: {exc}"})
                continue

            checked.append(name)
            if proc.returncode == 0:
                last = (proc.stdout.strip().splitlines() or [""])[-1][:160]
                findings.append({
                    "script": name,
                    "detail": (
                        f"exited 0 against an EMPTY repository, reporting "
                        f"{last!r}. A check that looked at nothing and reports "
                        "success is indistinguishable from one that works, and "
                        "reads green forever. Refuse (exit 1) with a message "
                        "naming what was not verified, or fail the precondition "
                        "(exit 2)."
                    ),
                })

    return {"findings": findings, "checked": checked, "skipped": skipped}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Guard: no shipped check reports success over empty input."
    )
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    root = (Path(args.root).resolve() if args.root
            else Path(__file__).resolve().parents[3])
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    report = scan(root)
    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if report["findings"] else 0

    print(f"Empty-input honesty: ran {len(report['checked'])} shipped check(s) "
          f"against an empty repository; {len(report['skipped'])} skipped.")
    for s in report["skipped"]:
        print(f"  skipped {s['script']}: {s['reason']}")

    if report["findings"]:
        print(f"\nCHECKS THAT PASS OVER NOTHING ({len(report['findings'])}):")
        for f in report["findings"]:
            print(f"  {f['script']}\n      {f['detail']}")
        print("\nA green result over an empty population is the one answer that "
              "is never true.")
        return 1

    if not report["checked"]:
        # This guard obeys the rule it enforces. Zero checks discovered means it
        # verified nothing, and saying so is the whole point of its existence.
        print("\nNOT A PASS: 0 shipped checks were discovered, so nothing was "
              "verified. Either --root points somewhere without a packaged "
              "plugin tree, or the discovery glob has stopped matching.")
        return 1

    print(f"\nAll {len(report['checked'])} checked script(s) refuse to report "
          "success over an empty population. Scope: this catches EMPTY input, "
          "not reduced input — a check matching 3 of 300 live cases still "
          "exits 0 here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
