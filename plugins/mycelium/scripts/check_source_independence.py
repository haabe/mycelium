#!/usr/bin/env python3
"""check_source_independence.py — enforce G-D2 and G-D4, which nothing enforced.

WHY (dogfood 2026-08-03, prompted by a peer practitioner). Two named guardrails
require evidence BREADTH, both declared `NUDGE`, both prose-only for the whole
life of the framework:

  G-D2  "Never treat a single interview as sufficient evidence. Require
         triangulation: at least 2 independent evidence types. Single-source
         evidence is anecdotal (0.3 on Gilad's confidence meter), regardless of
         how compelling it feels."
  G-D4  "Never validate opportunities using only one evidence type. Each
         opportunity in the OST must have evidence from at least 2 sources."

Grep for `G-D2` or `G-D4` across the repo and every hit is markdown:
`harness/guardrails.md`, `guardrails-discovery.md`, `guardrails-index.md`. No
script, no hook, no gate. A guardrail with a declared enforcement level and no
enforcement is the shape this project spent v0.77.0-v0.79.0 removing from its own
checks.

THE VOCABULARY COLLISION THAT KEPT THEM UNENFORCEABLE. G-D2 asks for "2
independent evidence types" and means METHOD — its own examples are "interviews +
behavioral data, or interviews + surveys". But `evidence_type` in
`_common.schema.json` is Gilad's confidence LADDER (speculation, anecdotal,
data-supported, test-validated, launch-validated). The guardrail names a field
that carries a different concept. The field that actually carries method is
`source_class` (external_human, external_data, internal_stakeholder,
internal_desk, internal_simulated), and neither guardrail references it. This
check binds the rule to the field that can answer it.

WHAT THIS MEASURES, stated narrowly because "independent" promises more than this
delivers. Rule 2 counts DISTINCT `source_class` values. Two interviews with two
different people are two sources but ONE method, and they share the method's
blind spot: both record what someone SAID, neither observes what they DID. This
is METHOD DIVERSITY, a proxy for independence and not independence.
  - It cannot see that two `external_data` snapshots came from one vendor.
  - It cannot see that five interviews were recruited from one channel.
  - It says nothing about sample size, recency, or quality.
A claim that clears this is not well-evidenced. It merely does not rest on a
single method.

SCOPE IS DELIBERATELY NARROW. G-D2 governs interpreting research findings and
G-D4 governs opportunities in the OST, so this reads discovery canvases only.
Applying it to `landscape.yml` was tried and rejected during construction: it
produced 8 findings, all competitor entries recorded once from one source, none
of them the thing either guardrail is about. A guard that fires outside its own
scope gets muted, and then it is not a guard.

WHY COVERAGE IS PRINTED BEFORE ANY VERDICT. `source_classes` is optional, and
unclassified sources default to `internal_desk` for ratio calculations. That
default is safe for the Source Ratio Sub-Check (it can only understate external
evidence) and actively misleading here: an unclassified 5-source claim looks
identical to real monoculture. Measured on the dogfood canvas 2026-08-03, a first
pass that trusted the default reported 40 findings and every one was an artefact.
The real numbers in scope were 47 provenance objects, 4 fully classified, 1
judgeable for rule 2. So the denominator ships with the verdict, always.

Exit codes:
  0 — no violations among judgeable claims (coverage still reported)
  1 — violations found, OR nothing judgeable at all (empty population)
  3 — PyYAML unavailable (SKIP, never a silent pass)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("SKIP:pyyaml unavailable", file=sys.stderr)
    sys.exit(3)

#: Gilad's ladder, weakest first.
LADDER = ["speculation", "anecdotal", "data-supported", "test-validated",
          "launch-validated"]
RANK = {name: i for i, name in enumerate(LADDER)}

#: G-D2's own number: single-source evidence is anecdotal, 0.3 on the meter.
SINGLE_SOURCE_CEILING_TYPE = "anecdotal"
SINGLE_SOURCE_CEILING_CONFIDENCE = 0.3

#: Rule 2 only bites on claims presented as established. Discovery legitimately
#: starts on one method; the guardrail is about what you then claim from it.
STRONG_TYPES = {"data-supported", "test-validated", "launch-validated"}
STRONG_CONFIDENCE = 0.6

#: G-D2/G-D4 both say "at least 2". Named so the rule is greppable and the
#: two comparisons below cannot drift apart.
MIN_SOURCES = 2

#: A pointer is a REFERENCE to another canvas entry, not evidence in itself, so
#: it is not a method and cannot contribute method diversity. It is EXCLUDED from
#: the diversity count and reported separately.
#:
#: CLASSIFYING a source as `pointer` is OBVIOUS and needs no human — the text
#: cites a canvas path. What is unknown is the TARGET's class, and that is a
#: different question from this source's class. The first version of this
#: conflated the two and called pointers "unresolved", which would have
#: manufactured an interview for the one classification that requires no
#: judgement (founder correction, 2026-08-03).
#:
#: The target is still not auto-resolved, for a separate reason: it is named in
#: free prose, so a resolver would be guessing at a citation — and copying the
#: target's class into the pointer duplicates a derived value, which goes stale
#: the moment the target is reclassified. That is the same defect that produced a
#: stale correction count and a stale gate heading the same week.
#: So the pointer IS classified; its target's contribution is simply not counted,
#: and the count set aside is printed so the limit is visible.
POINTER = "pointer"

# METHOD TAGS (added v0.91.0). Canvases annotate HOW a source was obtained inside
# the `evidence_sources[]` string — "juniors-dev-presentation [interventional — Frida
# named four-risks unprompted]". That is the method axis G-D2 actually asks about, and
# it was invisible to this check, which judged diversity over `source_class` alone.
#
# The 2026-08-05 dogfood consequence: need-001 carries observed behaviour, an
# unprompted articulation and an aggregation — three methods — and reported as
# single-coverage because all three are `external_human`. Acting on that report would
# have DOWNGRADED correctly-graded evidence. A check whose remedy damages the canvas is
# worse than one that stays quiet.
#
# Only genuine method markers count. Grade words that also appear in brackets
# (`anecdotal`, `data`, `speculation`) are ladder positions, not methods.
METHOD_TAGS = {
    # Human-research methods
    "behavior_validated",   # observed doing, not reported doing
    "interventional",       # articulated under a probe / unprompted in a live setting
    # Technical-evidence methods. Added v0.91.0 because the human vocabulary above
    # could not describe self-run technical work, and `external_data` was carrying all
    # of it: a five-run controlled experiment, a blind replication and log forensics
    # are three methods with three different blind spots and one source_class.
    "controlled_experiment",  # one-variable controls, exit codes, a stated control arm
    "blind_replication",      # reproduced by an agent/person given no access to the diagnosis
    "artifact_forensics",     # logs, caches, on-disk state — evidence that outlives the run
    "independent_report",     # someone else's published issue/data about the same behaviour
}

# Set aside like pointers, and for the same reason — they are not independent
# observation. `aggregated` is a roll-up of sources already counted elsewhere in the
# tree; `consistency_only` is correlation the project's own devils-advocate Technique 4
# exists to downgrade. Letting either supply the second method would let a weak source
# rescue a single-method claim, which is the anti-pattern this check serves.
NON_METHOD_TAGS = {"aggregated", "consistency_only"}

TAG_RE = re.compile("\\[([a-z][a-z_]{3,30}?)(?:\\s*[\u2014\\-\u2013]|\\])")


def _method_tags(prov):
    """Distinct method tags across a provenance block's evidence_sources.

    Returns (methods, set_aside). Empty methods means the canvas said nothing about
    method here and the caller must fall back to source_class.
    """
    methods, aside = set(), 0
    for src in prov.get("evidence_sources") or []:
        if not isinstance(src, str):
            continue
        for m in TAG_RE.finditer(src):
            tag = m.group(1).strip()
            if tag in METHOD_TAGS:
                methods.add(tag)
            elif tag in NON_METHOD_TAGS:
                aside += 1
    return methods, aside

#: G-D2 governs research findings, G-D4 governs the OST. Not the whole canvas.
DISCOVERY_CANVASES = ("opportunities.yml", "user-needs.yml", "scenarios.yml")

#: Printed verbatim when nothing is judgeable. check_empty_input_honesty
#: re-verifies this string against the file rather than trusting its table.
NO_VERDICT_MARKER = "NO BREADTH VERDICT AVAILABLE"


def _walk_provenance(node, path: str, out: list) -> None:
    """Collect every provenance object carrying an evidence_sources list."""
    if isinstance(node, dict):
        prov = node.get("provenance")
        if isinstance(prov, dict) and isinstance(prov.get("evidence_sources"), list):
            out.append((node.get("id") or path, prov))
        for key, value in node.items():
            _walk_provenance(value, f"{path}.{key}", out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk_provenance(value, f"{path}[{i}]", out)


def _overclaims_on_one_source(prov: dict) -> bool:
    """G-D2: one source cannot carry a claim above anecdotal / 0.3."""
    etype = prov.get("evidence_type")
    if etype in RANK and RANK[etype] > RANK[SINGLE_SOURCE_CEILING_TYPE]:
        return True
    conf = prov.get("confidence")
    return isinstance(conf, (int, float)) and conf > SINGLE_SOURCE_CEILING_CONFIDENCE


def _is_established(prov: dict) -> bool:
    conf = prov.get("confidence")
    if isinstance(conf, (int, float)) and conf >= STRONG_CONFIDENCE:
        return True
    return prov.get("evidence_type") in STRONG_TYPES



def _tagged_finding(tagged, ctx):
    """G-D2 verdict when the canvas declared its methods. None means it triangulates.

    Split out of scan() so this rule does not push that function past the complexity
    ceiling — the check that guards evidence quality should meet the repo's own.
    """
    if len(tagged) > 1:
        return []
    n = ctx["n"]
    return [{
        "rule": "G-D2", "file": ctx["name"], "id": str(ctx["ident"]), "sources": n,
        "source_class": min(tagged), "pointers_excluded": ctx["n_aside"],
        "confidence": ctx["prov"].get("confidence"),
        "detail": (
            f"{n} source(s) carrying ONE method, `{min(tagged)}` (judged on the "
            f"canvas's own method tags, not on source_class). Sources can differ and "
            f"still share a method's blind spot; G-D2 asks for 2+ independent methods. "
            f"Add a source obtained a different way, or lower the claim to match "
            f"single-method coverage."
        ),
    }]



def _single_source_finding(prov, name, ident, n):
    """RULE 1: one source carrying a claim above anecdotal. List, so callers branch once."""
    if n >= MIN_SOURCES or not _overclaims_on_one_source(prov):
        return []
    return [{
        "rule": "G-D2", "file": name, "id": str(ident), "sources": n,
        "evidence_type": prov.get("evidence_type"),
        "confidence": prov.get("confidence"),
        "detail": (
            f"one evidence source carrying `{prov.get('evidence_type')}` / "
            f"confidence {prov.get('confidence')}. G-D2: single-source evidence is "
            "anecdotal (0.3), regardless of how compelling it feels. Either add a "
            "second source or lower the claim."
        ),
    }]



def _diversity_finding(prov, classes, ctx, stats):
    """RULE 2: does this object's evidence span more than one METHOD?

    Lifted out of scan() in v0.91.0. The method-tag path added a branch that pushed
    scan past the repo's complexity ceiling, and a check that polices evidence quality
    should meet the repo's own code policy rather than raise it for itself.

    `stats` is mutated: pointers_excluded, unjudgeable_all_pointers,
    diversity_judgeable, methods_tagged. Returns a list of findings (0 or 1).
    """
    name, ident, n = ctx["name"], ctx["ident"], ctx["n"]
    methods = [c for c in classes if c != POINTER]
    n_ptr = len(classes) - len(methods)
    stats["pointers_excluded"] += n_ptr
    if not methods:
        stats["unjudgeable_all_pointers"] += 1
        return []

    # METHOD TAGS WIN WHEN THE CANVAS SUPPLIES THEM. `source_class` is a coarse proxy
    # for method: a controlled experiment, a blind replication and log forensics are
    # all `external_data`; observed behaviour and an unprompted articulation are both
    # `external_human`. Where the canvas annotated HOW a source was obtained, judge on
    # that rather than guessing from the class.
    tagged, tags_aside = _method_tags(prov)
    if tagged:
        stats["methods_tagged"] += 1
        stats["pointers_excluded"] += tags_aside
        stats["diversity_judgeable"] += 1
        return _tagged_finding(tagged, {
            "name": name, "ident": ident, "n": n,
            "n_aside": n_ptr + tags_aside, "prov": prov})

    stats["diversity_judgeable"] += 1
    if len(set(methods)) > 1:
        return []
    return [{
        "rule": "G-D2", "file": name, "id": str(ident), "sources": n,
        # Report the METHODS, not classes[0]. When pointers lead the list, classes[0]
        # is `pointer` and the message read "3 sources, all `pointer`" for an entry
        # whose single method was internal_desk — naming the wrong culprit on a correct
        # finding, which is how a true finding gets dismissed as a bug.
        "source_class": methods[0], "pointers_excluded": n_ptr,
        "confidence": prov.get("confidence"),
        "detail": (
            f"{len(methods)} evidence source(s), all `{methods[0]}`"
            + (f" ({n_ptr} pointer(s) set aside from {n} total)" if n_ptr else "")
            + f". The count says {len(methods)}; the coverage says one. Every source "
            "shares this method's blind spot, so the claim is supported no more "
            "broadly than a single source of this kind. G-D2 asks for 2+ independent "
            "evidence types, meaning methods, not repetitions."
        ),
    }]


def scan(root: Path) -> dict:
    """Classify every in-scope provenance object, then judge what is judgeable."""
    canvas_dir = root / ".claude" / "canvas"
    objects: list[tuple[str, str, dict]] = []
    unparseable: list[str] = []
    for name in DISCOVERY_CANVASES:
        path = canvas_dir / name
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception as exc:  # noqa: BLE001 — corrupt must not read as empty
            unparseable.append(f"{name}: {exc}")
            continue
        found: list = []
        _walk_provenance(data, "", found)
        objects.extend((name, ident, prov) for ident, prov in found)

    findings, classified = [], 0
    stats = {"pointers_excluded": 0, "unjudgeable_all_pointers": 0,
             "diversity_judgeable": 0, "methods_tagged": 0}
    for name, ident, prov in objects:
        n = len(prov["evidence_sources"])
        classes = prov.get("source_classes")
        fully = isinstance(classes, list) and len(classes) >= n
        if fully:
            classified += 1

        # RULE 1 (G-D2 / G-D4) — judgeable on every object, no classification needed.
        single = _single_source_finding(prov, name, ident, n)
        if single:
            findings.extend(single)
            continue

        # RULE 2 (G-D2 triangulation) — needs source_classes to say anything.
        if fully and n >= MIN_SOURCES and _is_established(prov):
            findings.extend(_diversity_finding(
                prov, classes, {"name": name, "ident": ident, "n": n}, stats))

    return {
        "root": str(root),
        "scope": list(DISCOVERY_CANVASES),
        "provenance_objects": len(objects),
        "fully_classified": classified,
        "diversity_judgeable": stats["diversity_judgeable"],
        "pointers_excluded": stats["pointers_excluded"],
        "methods_tagged": stats["methods_tagged"],
        "unjudgeable_all_pointers": stats["unjudgeable_all_pointers"],
        "findings": findings,
        "unparseable": unparseable,
    }


def verdict(result: dict) -> tuple[int, str]:
    """Exit code and headline computed ONCE, before any output branch.

    Deliberate: v0.77.0 found five scripts whose refuse-on-empty branch lived
    inside the `else` of `if args.json:`, so the machine-readable surface — the
    one a CI wrapper consumes — still exited 0 over an empty population.
    """
    if result["unparseable"]:
        return 1, f"UNPARSEABLE: {'; '.join(result['unparseable'])} — nothing judged"
    if result["provenance_objects"] == 0:
        return 1, (
            f"{NO_VERDICT_MARKER}: no provenance objects with evidence_sources in "
            f"{'/'.join(result['scope'])}. Refusing to report evidence breadth over "
            "an empty population."
        )
    if result["findings"]:
        return 1, (
            f"{len(result['findings'])} G-D2/G-D4 violation(s) across "
            f"{result['provenance_objects']} provenance object(s)"
        )
    return 0, (
        f"no breadth violations across {result['provenance_objects']} provenance "
        f"object(s) in scope"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="project root containing .claude/canvas")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    result = scan(Path(args.root))
    code, headline = verdict(result)

    if args.json:
        print(json.dumps({**result, "exit_code": code, "headline": headline}, indent=2))
        return code

    print(f"Evidence breadth (G-D2/G-D4) — {headline}")
    print()
    print(f"  scope                      : {', '.join(result['scope'])}")
    print(f"  provenance objects         : {result['provenance_objects']}")
    print(f"  declaring source_classes   : {result['fully_classified']}")
    if result.get("methods_tagged"):
        print(f"  judged on METHOD TAGS      : {result['methods_tagged']} "
              f"(the canvas said how the source was obtained; source_class was not guessed from)")
    print(f"  judgeable for triangulation: {result['diversity_judgeable']}")
    if result.get("pointers_excluded"):
        print(f"  pointer sources set aside   : {result['pointers_excluded']} "
              "(references, not methods — classified, but their targets'"
              " coverage is not counted here)")
    if result.get("unjudgeable_all_pointers"):
        print(f"  UNJUDGEABLE (all pointers)  : {result['unjudgeable_all_pointers']} "
              "object(s) cite only references, so they carry no evidence of "
              "their own. Cite what the targets cite, or accept the entry rests "
              "on other records rather than on sources.")
    for f in result["findings"]:
        print()
        print(f"  [{f['rule']}] {f['file']} #{f['id']}: {f['detail']}")
    unclassified = result["provenance_objects"] - result["fully_classified"]
    if unclassified:
        print()
        # NOT a violation, and must not read as one. It is the reason rule 2's
        # denominator is small, and saying so is the whole point.
        print(f"  {unclassified} object(s) declare no (or partial) `source_classes`, so")
        print("  triangulation could not be judged for them. That is a coverage limit,")
        print("  not a pass. See engine/theory-gates.md, Source Ratio Sub-Check.")
    return code


if __name__ == "__main__":
    sys.exit(main())
