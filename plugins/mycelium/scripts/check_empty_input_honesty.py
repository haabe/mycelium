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
import re
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
    "validate_canvas.py":
        "THREE-STATE BY DESIGN, and this guard only reads the exit code "
        "(added 2026-08-03). Its states are: no canvas dir -> N/A(0); canvas dir "
        "with zero .yml -> N/A(0); canvas with files -> PASS/FAIL. There is no "
        "state where it verifies nothing AND claims a pass, so it satisfies this "
        "guard's SPIRIT while exiting 0 on the empty case. Encoding N/A as a "
        "distinct exit code was considered and rejected: the shipped "
        "git-pre-push-example.sh treats any non-zero as failure, so it would "
        "re-block every push from a freshly /mycelium:setup project — the exact "
        "consumer breakage v0.75.1 and this release were fixing. The exemption is "
        "re-verified below against the file, not trusted from this table.",
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
AIM = {}

#: Exemptions are re-verified against the file every run, never trusted from the
#: table above. Each marker is the sentence the exemption's reason depends on.
STUB_MARKER = "DRAFT stub. Not yet implemented."
NA_MARKER = "This is NOT a pass over a populated canvas."


def _candidates(scripts_dir: Path) -> list[Path]:
    named = sorted(scripts_dir.glob("check_*.py"))
    for extra in ("validate_canvas.py", "verify_citations.py"):
        p = scripts_dir / extra
        if p.is_file():
            named.append(p)
    return named


#: argparse's own words when it rejects a flag we passed. If a child says this,
#: we never aimed it — its behaviour on empty input is UNKNOWN, not compliant.
#: argparse's exit code when it rejects the command line it was given.
ARGPARSE_USAGE_ERROR = 2

_UNAIMED = re.compile(
    r"unrecognized arguments|invalid choice|error: argument|no such option", re.IGNORECASE
)


def _mentions_root(script: Path) -> bool:
    """Cheap pre-filter only. NEVER the compliance decision.

    Code review 2026-08-03: this used to BE the decision, as a substring test over
    the whole file — so a script whose docstring merely said `it does not accept
    "--root"` was judged aimable, run with a flag it rejects, exited 2 from
    argparse, and was counted as an honest refusal. A check that always reports
    green was certified compliant. The real decision now comes from running it and
    reading what argparse said; this only avoids launching obviously-irrelevant
    scripts.
    """
    src = script.read_text(errors="replace")
    return '"--root"' in src or "'--root'" in src


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
        # The fixture must MEET each check's precondition while leaving its
        # population empty — otherwise every check answers "N/A" here and the
        # guard verifies nothing while reporting a pass. Precondition-absent and
        # population-empty are different states and this is where they diverge.
        (empty / SCRIPTS_REL).mkdir(parents=True)
        (empty / "plugins" / "mycelium" / "hooks").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=empty, check=False,
                       capture_output=True)

        for script in _candidates(scripts_dir):
            name = script.name
            if name in EXEMPT:
                reason = EXEMPT[name]
                src = script.read_text(errors="replace")
                stale = (
                    (name == "check_gated_by.py" and STUB_MARKER not in src)
                    or (name == "validate_canvas.py" and NA_MARKER not in src)
                )
                if stale:
                    findings.append({
                        "script": name,
                        "detail": (
                            "EXEMPT ON A REASON THAT IS NO LONGER TRUE. The file "
                            "no longer carries the marker its exemption rests on "
                            f"({STUB_MARKER!r} for the stub, {NA_MARKER!r} for the "
                            "three-state canvas validator). An exemption outlives "
                            "its justification silently, which is a hole exactly "
                            "where someone stopped looking. Re-verify or remove it."
                        ),
                    })
                else:
                    skipped.append({"script": name, "reason": reason})
                continue

            extra = AIM.get(name)
            if extra is None and not _mentions_root(script):
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

            # DID WE ACTUALLY AIM IT? An argparse usage error means the child
            # never ran its own logic, so its empty-input behaviour is unknown.
            # Counting that as a refusal is how the guard certified a check it
            # never executed (code review 2026-08-03).
            if (proc.returncode == ARGPARSE_USAGE_ERROR
                    and _UNAIMED.search(proc.stderr or "")):
                skipped.append({
                    "script": name,
                    "reason": (
                        "REJECTED THE FLAGS WE AIMED IT WITH "
                        f"({(proc.stderr or '').strip().splitlines()[-1][:120]}). "
                        "It never ran its own logic, so its empty-input behaviour "
                        "is UNKNOWN — not compliant. Add an AIM entry so it can "
                        "be tested, or this is a hole in the guard."
                    ),
                })
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

    if not (root / SCRIPTS_REL).is_dir():
        print(f"Empty-input honesty: N/A — no {SCRIPTS_REL}/ under {root}. This "
              "guard runs the FRAMEWORK repo's shipped checks; a plugin consumer "
              "ships none of its own. Nothing was checked, and nothing was "
              "supposed to be.")
        return 0

    report = scan(root)
    # Verdict decided BEFORE the output branch (code review 2026-08-03). The JSON
    # path returned `1 if findings else 0`, which ignores the zero-checks-
    # discovered refusal below — so THIS GUARD had the very defect it exists to
    # catch, on its own machine-readable surface.
    rc = 1 if (report["findings"] or not report["checked"]) else 0
    if args.json:
        print(json.dumps({**report, "verdict": "fail" if rc else "pass"}, indent=2))
        return rc

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
