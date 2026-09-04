#!/usr/bin/env python3
"""Evidence landed. Was the confidence it bears on ever looked at again?

THE DEFECT THIS EXISTS FOR, MEASURED ON THE DOGFOOD PROJECT 2026-09-04. A diamond's confidence had
moved exactly ONCE in the project's history. In the twenty days since, four sweeps ran, a
pre-registered test scored SUPPORTS on the first attribution evidence the bet had ever had, and a
crossing condition written IN ADVANCE -- "sweep 2 reproducing the nine through a different family is
what earns the crossing" -- was met three times over. **The number did not move, and nobody noticed
it should.** The founder's words: "I am so sick of asking you to help me find the tools needed to
find the evidence, and then just going in circles without nudging the evidence one tiny bit."

WHY IT HAPPENED, AND IT IS NOT LAZINESS. Two mechanical causes, both fixable:

  1. **FIVE SKILLS MANDATE UPDATING CONFIDENCE AND NO CHECK VERIFIED IT.** assumption-test,
     log-evidence, handoff, ost-builder and launch-tier all instruct it. The only occurrence of
     "stale confidence" anywhere in the framework was an EXAMPLE STRING inside a report template.
     A rule with no reader does not bind -- the same shape as the DL-id convention and the
     version-bump rule, both also found the same day.

  2. **THE DERIVATION WAS STORED IN A YAML COMMENT AND A LATER REWRITE DELETED IT.** The components,
     the open items and the crossing condition survived only in a decision-log entry nobody diffed
     against new evidence. **Comments are not data.** Any derivation that must be re-read must be a
     FIELD.

WHAT THIS CHECK DOES *NOT* DO, and the distinction is the whole design. **It never demands that a
number MOVE.** Evidence can legitimately arrive and leave a value unchanged -- a finding, not
a failure, and a check that pushed numbers upward would be an inflation engine pointed at the one
value a project must not inflate. **It demands only that somebody LOOKED**, and that the looking is
recorded with a date. Considered-and-unchanged is a pass. Unconsidered is the defect.

OPT-IN BY PRESENCE, like the rest of the framework: a diamond with no `confidence_derivation` block
is not judged on one. What IS judged is the pairing -- if a diamond names open components with a
`closed_by` condition, and that condition's evidence has since landed, the block must have been
revisited.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

# NO TIME THRESHOLD. THE FIRST VERSION HAD ONE AND IT WAS BLIND (2026-09-04).
# It used STALE_DAYS = 30, and the defect it was built for was a TWENTY-day gap, so the guard
# passed the exact case that motivated it. A threshold picked without checking it against the known
# instance is how a guard ships green and measures nothing -- and this project has caught that
# shape repeatedly, most recently in a detector whose recall on known positives was zero.
#
# The trigger is EVIDENCE, not elapsed time, per the standing rule that an alarm fires on evidence
# the event happened rather than on a date advancing. One scored instrument that names this diamond
# is enough: it means something was learned and nobody asked what it did to the number.
MIN_INSTRUMENTS = 1
PREVIEW = 3          # instrument names shown before eliding


def _git(root, *args):
    r = subprocess.run(("git", "-C", str(root), *args), capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def _parse_date(v):
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except (TypeError, ValueError):
        # SPEAKS, per anti-pattern #9: a silent None here would surface downstream as
        # "no changed_at", which is a different defect from "the date is unparseable".
        print(f"  note: could not parse date {v!r} — treating as absent", file=sys.stderr)
        return None


def diamonds(root: Path):
    p = root / ".claude/diamonds/active.yml"
    if not p.exists():
        return []
    try:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        # SPEAKS, and this is the one that mattered. A silent [] here reaches the caller as
        # "no diamonds found", and the operator is told their project has no diamonds when the
        # truth is that their canvas will not parse. Same reading, two very different problems.
        print(f"  ERROR: {p} could not be read or parsed ({type(e).__name__}: {e}). "
              f"NOTHING WAS VERIFIED.", file=sys.stderr)
        return []
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and "confidence" in o:
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return out


def evidence_since(root: Path, since: date, diamond_id: str | None = None) -> list[str]:
    """Scored instruments that NAME this diamond, committed after `since`.

    Target-aware on purpose: an instrument about a different diamond is not evidence about this
    number, and counting it would train the reader to ignore the warning."""
    hits = []
    for f in (root / ".claude/evals/assumption-tests").glob("*.md"):
        try:
            txt = f.read_text(encoding="utf-8")
        except OSError:
            continue
        if "status: scored" not in txt:
            continue
        if diamond_id and diamond_id not in txt:
            continue
        # date the scoring by the file's last commit, not mtime -- mtime moves on checkout
        # Git first: a commit date survives checkout, where mtime does not.
        iso = _git(root, "log", "-1", "--format=%ad", "--date=short", "--", str(f))
        d = _parse_date(iso)
        if d is None:
            # FALLBACK, and it is load-bearing. Outside a git repo (a fresh install, a consumer who
            # has not committed yet, a test fixture) `git log` returns nothing and the guard would
            # find no evidence and report a silent pass — the blindness this whole check exists to
            # prevent, reproduced inside the check itself.
            d = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC).date()
        if d and d > since:
            hits.append(f.name)
    return sorted(hits)


def audit(root: Path, today: date | None = None) -> list[dict]:
    today = today or datetime.now(UTC).date()
    findings = []
    for dm in diamonds(root):
        der = dm.get("confidence_derivation")
        if not isinstance(der, dict):
            # Not opted in. Fall back to the weakest useful signal: has the value EVER been derived?
            findings.append({"id": dm.get("id"), "level": "INFO",
                             "msg": "no `confidence_derivation` block — the number cannot be "
                             "re-derived by anyone, only re-asserted"})
            continue
        changed = _parse_date(der.get("changed_at"))
        if not changed:
            findings.append({"id": dm.get("id"), "level": "WARN",
                             "msg": "`confidence_derivation` has no `changed_at`; staleness "
                                    "is unmeasurable"})
            continue
        age = (today - changed).days
        ev = evidence_since(root, changed, dm.get("id"))
        n_ev = len(ev)
        opens = [c for c in (der.get("components") or [])
                 if str(c.get("status", "")).upper() == "OPEN"]
        closers = [c for c in opens if c.get("closed_by")]
        if n_ev >= MIN_INSTRUMENTS:
            findings.append({
                "id": dm.get("id"), "level": "WARN", "instruments": ev,
                "msg": (f"{n_ev} scored instrument(s) naming this diamond landed in the {age} days "
                     f"since its confidence was derived, and it has not been revisited. "
                     f"Re-derive, or record considered-and-unchanged with a date — unchanged is a "
                     f"pass, unexamined is not. ({', '.join(ev[:3])}"
                        f"{', …' if n_ev > PREVIEW else ''})")})
        if closers:
            findings.append({
                "id": dm.get("id"), "level": "INFO",
                "msg": (f"{len(closers)} open component(s) name a `closed_by` condition. Check it "
                     f"against evidence landed since {changed}: "
                        + "; ".join(str(c.get("name")) for c in closers))})
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    # EMPTY-INPUT HONESTY. A green over a population of zero is the one answer that is never true:
    # it is indistinguishable from a working check and reads green forever. Refuse instead, naming
    # what was NOT verified. Caught by the framework's own check_empty_input_honesty on first run.
    # THREE STATES, NOT TWO. Conflating them blocked this check's own first push (2026-09-04):
    # the framework tree carries `active_diamonds: []`, an explicit empty list, and the check
    # called that "precondition unmet" and exited 2.
    #
    #   file ABSENT              -> refuse (2). Nothing to verify and no way to know that is meant.
    #   file present, UNPARSEABLE -> refuse (2). The handler in `diamonds()` names the error.
    #   file present, DECLARES ITSELF EMPTY -> N/A (0). Per this framework's own rule, an empty
    #       file that DECLARES itself empty is a decision; only one that declares itself fresh is
    #       a defect. A project with no diamonds yet must not be failed for having none.
    dpath = root / ".claude/diamonds/active.yml"
    if not dpath.exists():
        print(f"PRECONDITION UNMET: {dpath} does not exist. NOTHING WAS VERIFIED — not a pass.",
              file=sys.stderr)
        return 2
    if not diamonds(root):
        try:
            raw = yaml.safe_load(dpath.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return 2                       # `diamonds()` already named the error on stderr
        if raw is None:
            print(f"PRECONDITION UNMET: {dpath} is empty and says nothing about why. "
                  f"NOTHING WAS VERIFIED — not a pass.", file=sys.stderr)
            return 2
        print(f"N/A: {dpath} declares no diamonds. Nothing to check, and the file says so — "
              f"a project with no diamonds yet is a decision, not a defect.")
        return 0
    f = audit(root)
    if a.json:
        print(json.dumps(f, indent=1))
    else:
        n_d = len(diamonds(root))
        n_derived = sum(1 for d in diamonds(root)
                        if isinstance(d.get("confidence_derivation"), dict))
        if not [x for x in f if x["level"] == "WARN"]:
            print(f"OK: {n_derived} of {n_d} diamond(s) carry a derivation and none has unexamined "
                  f"evidence. OUTSIDE THIS COUNT: {n_d - n_derived} diamond(s) with no "
                  f"`confidence_derivation` block — not failed, but their numbers can only be "
                  f"re-asserted, never re-derived.")
        for x in f:
            print(f"  {x['level']:5s} {x['id']}: {x['msg']}")
        print("\nA number that did not move is fine. A number nobody looked at is the defect.")
    return 1 if any(x["level"] == "WARN" for x in f) else 0


if __name__ == "__main__":
    raise SystemExit(main())
