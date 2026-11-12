#!/usr/bin/env python3
"""Re-check surfaced upstream candidates against the live framework tree.

WHAT THIS IS FOR. Framework changes flow one way out of this repo: surfaced here,
authored upstream, shipped in a release. Nothing ever walked back to mark the
roadmap entry closed, and the decision log is append-only, so a shipped candidate
reads as open forever. A ground-truth pass on 2026-08-17 found SIX OF TEN already
shipped. The 2026-06-12 gap analysis had found 4 of 6 and written down "diff, don't
rediscover"; the pile regrew to the same composition inside two months.

So this checker exists to report DISAGREEMENT between what the registry believes and
what the tree contains, in both directions:

  LANDED    status: open, but the probe finds the change. Close the entry.
  REGRESSED status: shipped, but the probe no longer finds it. Go and look.

"Open" here is every status that is not a closed one (CLOSED_STATUSES below):
`surfaced`, `proposed`, `reopened_...` and any other word an author writes for
"not settled yet" are read under the open rule. Until this was widened only the
literal `open` could ever say LANDED, and a registry that had grown eight more
statuses held 59 probes that could not report the one thing the file is for.

It deliberately does NOT auto-update the registry. A checker that silently retargeted
would be the same fail-open the dependency-drift check exists to avoid — and closing a
candidate is a judgement about whether the thing that was asked for is what landed.

UNVERIFIABLE IS ITS OWN OUTCOME. A candidate with `verify: null` is reported, not
skipped. An item nothing can check is how the pile grew, and hiding those behind a
green summary would rebuild the problem inside the fix.
"""
from __future__ import annotations

import argparse
import glob as globlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

LANDED = "LANDED"
REGRESSED = "REGRESSED"
AGREES = "agrees"
UNVERIFIABLE = "unverifiable"
UNREADABLE = "unreadable"

# Consumer-relative: the registry lives in the USER's project, not in the plugin.
#: Candidates surfaced on or after this date must carry a `different_builder:` sentence.
SCENARIO_RULE_DATE = "2026-09-11"
DEFAULT_REGISTRY = Path(".claude/harness/upstream-candidates.yml")

# Statuses that close a candidate. Read from the dogfood registry 2026-11-12, which
# uses these five plus open-like ones (open, surfaced, proposed, reopened_on_proposal_b,
# open-but-headline-retracted); `retracted` is listed because the 2026-10-11 count of
# that registry named a retracted candidate. `shipped` is the one closed status with its own probe
# rule (REGRESSED); the rest are closed with no claim about the tree, so their probes
# are not compared. Every status NOT in this set is open for the probe and for the
# different-builder rule: an unknown word is far more often "not yet" than "done", and
# reading it as open costs at most a LANDED line a human then reads.
CLOSED_STATUSES = frozenset({
    "shipped", "declined", "withdrawn", "retracted", "resolved-by-design",
    "no-longer-reproduces",
})

# The three rules a probe can be read under, for the per-rule counts on every run.
RULE_OPEN = "open rule (LANDED if the change is in the tree)"
RULE_SHIPPED = "shipped rule (REGRESSED if the change is gone)"
RULE_CLOSED = "closed, not compared"


def _status(entry: dict) -> str:
    return str(entry.get("status") or "open").strip()


def is_open(entry: dict) -> bool:
    """Not closed. A missing status is open, as it always was in classify()."""
    return _status(entry) not in CLOSED_STATUSES


def probe_rule(entry: dict) -> str:
    status = _status(entry)
    if status == "shipped":
        return RULE_SHIPPED
    return RULE_CLOSED if status in CLOSED_STATUSES else RULE_OPEN

# Where the framework tree might be, most specific first. CI checks the framework
# out beside the roadmap; locally it is either the plugin cache or the operator's
# clone, whose path is recorded in .claude/state/upstream.json.
def framework_roots(explicit: str | None) -> list[Path]:
    if explicit:
        return [Path(explicit)]
    roots: list[Path] = []
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        # CLAUDE_PLUGIN_ROOT points AT plugins/mycelium; probes are repo-relative.
        roots.append(Path(env).resolve().parents[1])
    roots.append(Path("mycelium"))  # CI: actions/checkout path: mycelium
    state = Path(__file__).resolve().parents[2] / "state" / "upstream.json"
    try:
        repo = json.loads(state.read_text()).get("upstream_repo")
        if repo:
            roots.append(Path(repo))
    except (OSError, ValueError):
        pass
    return roots


def resolve_root(explicit: str | None) -> Path | None:
    for r in framework_roots(explicit):
        if (r / "plugins" / "mycelium").is_dir():
            return r
    return None


def probe(verify: dict | None, root: Path) -> tuple[bool | None, str]:
    """Return (found, detail). `found is None` means the probe could not run —
    which is never the same as 'not found'."""
    if not verify:
        return None, "no probe declared"
    if "glob" in verify:
        hits = globlib.glob(str(root / verify["glob"]))
        return bool(hits), (f"{len(hits)} path(s) match {verify['glob']}")
    target = root / verify["file"]
    if not target.exists():
        return None, f"{verify['file']} does not exist in the tree"
    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return None, f"could not read {verify['file']}: {exc}"
    pattern = verify.get("pattern", ".")
    hit = bool(re.search(pattern, text))
    return hit, f"pattern {'found' if hit else 'absent'} in {verify['file']}"


def classify(entry: dict, root: Path) -> tuple[str, str]:
    rule = probe_rule(entry)
    found, detail = probe(entry.get("verify"), root)
    if found is None:
        return (UNVERIFIABLE if entry.get("verify") is None else UNREADABLE), detail
    expect_present = (entry.get("verify") or {}).get("expect", "present") == "present"
    satisfied = found if expect_present else not found
    # `satisfied` means: the tree looks the way this status claims it should.
    if rule == RULE_SHIPPED:
        return (AGREES, detail) if satisfied else (REGRESSED, detail)
    if rule == RULE_OPEN:
        return (LANDED, detail) if not satisfied else (AGREES, detail)
    return AGREES, detail


def _first_line(text: str | None) -> str:
    """First line of an optional field, or a stated absence.

    `"".splitlines()` is `[]`, so indexing [0] raises IndexError on an entry whose
    field is missing or blank — which crashed the REGRESSED report, the one path
    that matters most. Found by the negative-control test for this guard, because
    every shipped entry in the dogfood registry happens to carry a note and the
    crash could not surface there.
    """
    lines = (text or "").strip().splitlines()
    return lines[0][:90] if lines else "(no note recorded)"


def _no_scenario(entries: list) -> list:
    """Candidates surfaced on or after the rule date with no `different_builder:` sentence.

    OPEN CANDIDATES ONLY. The sentence exists to decide whether a finding is a framework
    finding; once a candidate has shipped, been declined, withdrawn or retracted, no
    decision is left for it to change, and failing --strict on it asked for exactly the
    bulk backfill the rule rules out. Measured on the dogfood registry 2026-10-11: 34
    rows without a sentence, 17 of them already closed.
    """
    return [
        e for e in entries
        if is_open(e)
        and str(e.get("surfaced", "")) >= SCENARIO_RULE_DATE
        and not str(e.get("different_builder") or "").strip()
    ]


def _report_no_scenario(no_scenario: list) -> None:
    if not no_scenario:
        return
    print(f"\nNO DIFFERENT-BUILDER SCENARIO — {len(no_scenario)} open candidate(s) surfaced on "
          f"or after {SCENARIO_RULE_DATE} carry no `different_builder:` sentence. A finding that\n"
          "cannot say what it looks like for another builder on another product has not shown\n"
          "it is a framework finding (engine/agent-operating-contract.md):")
    for e in no_scenario:
        print(f"  {e['id']}  (surfaced {e.get('surfaced', '?')})")


def _report_rule_counts(results: list) -> None:
    """How many probes were read under each rule, and which statuses fed the open rule.

    Printed on every run so a status the check reads differently from its author's
    intent is visible in the output, not only in this file.
    """
    counts = {RULE_OPEN: 0, RULE_SHIPPED: 0, RULE_CLOSED: 0}
    open_statuses = set()
    for entry, verdict, _detail in results:
        if verdict in (UNVERIFIABLE, UNREADABLE):
            continue
        rule = probe_rule(entry)
        counts[rule] += 1
        if rule == RULE_OPEN:
            open_statuses.add(_status(entry))
    print("\nProbes evaluated per rule:")
    for rule, n in counts.items():
        extra = ""
        if rule == RULE_OPEN and n:
            extra = f"  [statuses: {', '.join(sorted(open_statuses))}]"
        print(f"  {n:4d}  {rule}{extra}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--framework-root", default=None)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on LANDED, REGRESSED, or a new candidate with no scenario")
    args = ap.parse_args(argv)


    reg_path = Path(args.registry)
    if not reg_path.exists():
        print(f"ERROR: registry not found at {reg_path}", file=sys.stderr)
        return 2
    registry = yaml.safe_load(reg_path.read_text()) or {}
    entries = registry.get("candidates") or []

    # THE DIFFERENT-BUILDER TEST (engine/agent-operating-contract.md, founder ruling
    # 2026-09-11). A candidate surfaced on or after the rule date must carry one sentence
    # saying what the finding looks like for a different builder on a different product.
    # Earlier candidates are not backfilled: a bulk backfill is the filler trap the rule
    # exists to avoid. Reported always; fails only under --strict.
    no_scenario = _no_scenario(entries)

    root = resolve_root(args.framework_root)
    if root is None:
        # Cannot see the tree: report that, do not report agreement.
        print("Upstream candidate registry")
        print("=" * 60)
        print(f"  ??    framework tree not found (looked in "
              f"{', '.join(str(p) for p in framework_roots(args.framework_root))})")
        print(f"\n{len(entries)} candidate(s) NOT verified — no framework tree to check against.")
        return 0

    results = [(e, *classify(e, root)) for e in entries]
    marks = {LANDED: "LANDED", REGRESSED: "REGRESS", AGREES: "  ok   ",
             UNVERIFIABLE: "  ??   ", UNREADABLE: "  ??   "}

    print("Upstream candidate registry")
    print("=" * 60)
    print(f"tree: {root}")
    for entry, verdict, detail in results:
        print(f"{marks[verdict]}  {entry['id']}: {detail}")

    landed = [e for e, v, _ in results if v == LANDED]
    regressed = [e for e, v, _ in results if v == REGRESSED]
    unver = [e for e, v, _ in results if v in (UNVERIFIABLE, UNREADABLE)]

    if landed:
        print("\nLANDED — these are marked open but the change is IN THE TREE. This is the\n"
              "whole point of the file: shipped work reading as open is what made the pile\n"
              "look like a backlog. Close them, or say why the probe is wrong:")
        for e in landed:
            head = _first_line(e.get("summary"))
            print(f"  {e['id']}  (surfaced {e.get('surfaced', '?')}) — {head}")
    if regressed:
        print("\nREGRESSED — marked shipped, but the probe can no longer find it:")
        for e in regressed:
            print(f"  {e['id']} — {_first_line(e.get('landed_note'))}")
    if unver:
        print(f"\n{len(unver)} candidate(s) carry no usable probe. Reported rather than\n"
              "skipped: an item nothing can check is how this pile grew.")
        for e in unver:
            print(f"  {e['id']}")

    _report_no_scenario(no_scenario)

    _report_rule_counts(results)

    open_n = sum(1 for e in entries if is_open(e))
    print(f"\n{len(entries)} candidates: {open_n} open (any status not closed), "
          f"{sum(1 for e in entries if _status(e) == 'shipped')} shipped, "
          f"{len(landed)} LANDED, {len(regressed)} REGRESSED, {len(unver)} unverifiable")
    return 1 if (args.strict and (landed or regressed or no_scenario)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
