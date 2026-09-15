#!/usr/bin/env python3
"""check_source_class_fidelity.py — the label has to match the source it labels.

THE GAP, AND WHY THE TWO NEIGHBOURING CHECKS DO NOT COVER IT.

`check_source_authenticity.py` asks whether a cited human is a real human.
`check_source_independence.py` asks whether a claim rests on more than one method.
Both take `source_classes` AT ITS WORD. Nothing anywhere asks the prior question:
**does this class describe the thing sitting next to it?**

FOUND IN DOGFOOD 2026-08-08, on a direct question from the founder ("look for other
gaps where my founder-as-a-user status is logged as something else"). A mechanical
sweep of all 25 canvas files found **ten founder-sourced entries: five correctly
`internal_stakeholder`, five claiming `external_human`** — opp-008, sol-008a, scn-004,
scn-006, scn-007. `external_human` is the field that means *someone outside this project
said so*. The founder is the project.

THREE THINGS MAKE IT WORSE THAN A TYPO.

  1. **The prose already knew, in three of the five.** scn-004's own source text reads
     "[anecdotal, non-arms-length]" beside a class of external_human. scn-007 carries a
     sibling `source_class: internal_desk` whose comment says "NO external human has..."
     four lines above a `source_classes` array claiming external_human twice. The
     comment a human reads and the field a script reads, disagreeing inside one block.

  2. **It is machine-consumed.** check_source_independence counts DISTINCT
     `source_class` values as method diversity. A founder mislabelled `external_human`
     manufactures diversity that does not exist, so a claim resting on one person plus
     desk research reads as corroborated.

  3. **It inflates in the direction of comfort.** All nine mislabels found pointed the
     same way: toward more external evidence than exists. Nobody mislabels an outside
     voice as internal.

WHAT THIS CHECKS. Two rules, both narrow, precision chosen over recall because a false
positive here costs a maintainer an argument with a correct record.

  RULE 0 — ALIGNMENT. `evidence_sources` and `source_classes` must be the same length.
  They are index-parallel (established empirically: 60 blocks in one dogfood canvas
  carry duplicate class values, which a set could not). When the lengths differ, every
  pairing after the first difference is meaningless and Rule 1 cannot be evaluated at
  all. This is a precondition, reported separately from Rule 1.

  RULE 1 — FIDELITY. A source may not be classed `external_human` when the source text
  itself says it is not a person outside the project. Three detectors, in descending
  confidence:

    (a) SELF-LABEL CONTRADICTION. The source opens with an inline provenance tag —
        `[artifact_forensics]`, `[internal_desk]`, `[controlled_experiment]`,
        `[internal_simulated]`, `[internal_stakeholder]` — that contradicts the class
        beside it. Zero interpretation: the record labels itself twice and disagrees.
    (b) THE PROJECT'S OWN VOICE. The source opens with `Founder`, or names a
        self-report / self-identification / founder-dogfood.
    (c) NOT A PERSON AT ALL. The source names a dogfood run, a subagent, a simulation,
        or opens with a filesystem path or `<X> repo`.

WHAT IT DELIBERATELY DOES NOT CATCH, stated so a pass is not read as more than it is:

  * **A pointer to genuinely external evidence.** `human-tasks.yml#ht-058 — Frida,
    churn interview` cites a file but the evidence is a real outside person. Flagging
    every source containing a file path would fire on those, so file paths alone are
    NOT a detector. The cost is real misses: a source reading "OBSERVED INSTANCE
    2026-08-04: human-tasks.yml#ht-002 closed..." classed external_human is wrong and
    this check will not see it.
  * **`source_class` (singular) disagreeing with `source_classes` (plural).** Both
    field spellings are schema-valid since v0.16.2 (the Postel's-law fix) and in dogfood
    they have drifted apart. That is a real defect and a different one.
  * **Whether a correctly-shaped class is the RIGHT class.** "external_data" on a
    source that is really "external_human" is invisible here. This asks only whether a
    class is contradicted by its own source text.

A clean run means no source contradicts its own label by these three detectors. It does
not mean the classes are right.
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
    print("check_source_class_fidelity: PyYAML not installed", file=sys.stderr)
    sys.exit(2)

CANVAS_REL = ".claude/canvas"

#: The class this check polices. Only this one inflates an evidence ledger.
GUARDED_CLASS = "external_human"

#: (a) Inline provenance tags that contradict `external_human` when they open a source.
#: These are a convention already in use in dogfood canvases; a source carrying one is
#: labelling itself, and the label loses to nothing.
CONTRADICTING_TAG = re.compile(
    r"^\s*\[(artifact_forensics|internal_desk|internal_simulated|"
    r"internal_stakeholder|controlled_experiment|independent_report|pointer)\]",
    re.IGNORECASE,
)

#: (b) The project's own voice. ANCHORED AT THE START on purpose: "founder-relayed",
#: "non-founder", "solo-founder" and "the founder's own concession" all appear inside
#: legitimately-external sources, and matching them would fire on real outside voices.
SELF_VOICE = re.compile(
    r"^\s*(\[[a-z_]+\]\s*)?Founder\b"
    r"|^\s*(\[[a-z_]+\]\s*)?Self-report\b"
    r"|founder-dogfood"
    r"|self-identification",
    re.IGNORECASE,
)

#: (c) Things that are not people. `subagent`/`simulated`/`dogfood run` are never an
#: outside human; a leading path or "<X> repo" is a tree, not a voice.
NOT_A_PERSON = re.compile(
    r"auto-dogfood|dogfood run|subagent|haiku-simulated|\bsimulated\b"
    r"|^\s*(\[[a-z_]+\]\s*)?/"
    r"|^\s*(\[[a-z_]+\]\s*)?\w[\w .-]* repo[: ]",
    re.IGNORECASE,
)

DETECTORS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "self-label-contradiction",
        CONTRADICTING_TAG,
        "the source opens with an inline provenance tag that contradicts its class",
    ),
    (
        "project-own-voice",
        SELF_VOICE,
        "the source is the project speaking about itself, not an outside human",
    ),
    (
        "not-a-person",
        NOT_A_PERSON,
        "the source names a run, a simulation or a tree, which is not a human at all",
    ),
]


def classify(source: str) -> tuple[str, str] | None:
    """Return (detector_name, why) for the first detector that fires, else None."""
    for name, pattern, why in DETECTORS:
        if pattern.search(source):
            return name, why
    return None


def _walk(node, filename: str, ident, misalignments: list, violations: list) -> None:
    if isinstance(node, dict):
        ident = node.get("id") or node.get("scenario_id") or ident
        if isinstance(node.get("evidence_sources"), list) and isinstance(
                node.get("source_classes"), list):
            _evaluate_block(node, filename, ident, (misalignments, violations))
        for value in node.values():
            _walk(value, filename, ident, misalignments, violations)
    elif isinstance(node, list):
        for item in node:
            _walk(item, filename, ident, misalignments, violations)


def _evaluate_block(node: dict, filename: str, ident, out: tuple[list, list]) -> None:
    """One provenance block: reviewed markers, the one-class convention, alignment, labels.

    REVIEWED MARKERS (v0.190.0). `alignment_reviewed: {date, reason}` on the block says a
    human read the unequal arrays and ruled them a coverage state; it is reported as reviewed
    coverage, never as FAIL, and the one-class convention below is NOT applied over a human
    ruling. `label_reviewed: [{index, date, reason}]` says a specific source's label was read
    against its text and stands; that index is skipped.

    ONE-CLASS CONVENTION (v0.210.0). The schema's singular `source_class` is the sanctioned
    form for "every source is the same class"; a block that wrote that intent as a one-item
    `source_classes` list beside N sources is the same claim in the other spelling (21 of the
    42 dogfood misalignments on 2026-08-30). It is expanded and its labels evaluated, not
    reported as unequal arrays.
    """
    misalignments, violations = out
    sources, classes = node["evidence_sources"], node["source_classes"]
    reviewed = node.get("alignment_reviewed")
    is_reviewed = bool(isinstance(reviewed, dict) and reviewed.get("date"))
    label_ok = {
        int(r["index"])
        for r in (node.get("label_reviewed") or [])
        if isinstance(r, dict) and str(r.get("index", "")).lstrip("-").isdigit()
    }
    if len(classes) == 1 and len(sources) > 1 and not is_reviewed:
        classes = classes * len(sources)
    if len(sources) != len(classes):
        misalignments.append({
            "file": filename, "id": ident, "sources": len(sources), "classes": len(classes),
            "reviewed": is_reviewed,
            "reviewed_reason": reviewed.get("reason", "") if isinstance(reviewed, dict) else "",
        })
        return
    for i, (src, cls) in enumerate(zip(sources, classes, strict=True)):
        if not isinstance(src, str) or cls != GUARDED_CLASS or i in label_ok:
            continue
        hit = classify(src)
        if hit:
            violations.append({
                "file": filename, "id": ident, "index": i,
                "detector": hit[0], "why": hit[1], "source": src[:160],
            })


def evaluate(root: Path) -> dict:
    canvas = root / CANVAS_REL
    if not canvas.is_dir():
        return {"status": "no-canvas", "canvas_dir": str(canvas)}

    files = sorted(canvas.glob("*.yml"))
    violations: list[dict] = []
    misalignments: list[dict] = []
    parsed = 0
    unreadable: list[dict] = []

    for path in files:
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
            # A canvas that will not parse is a FINDING, not a skip: a check that
            # silently ignores unreadable input reports success over a population it
            # never saw.
            unreadable.append({"file": path.name, "error": str(exc)[:120]})
            continue
        parsed += 1
        _walk(data, path.name, None, misalignments, violations)

    if parsed == 0:
        return {
            "status": "nothing-examined",
            "files_found": len(files),
            "unreadable": unreadable,
        }

    # TWO VERDICTS, SEPARATED (v0.210.0). A label contradicted by its own source text is a
    # defect and fails. Unequal arrays are a COVERAGE state: the operating contract that
    # created the field says the class is set at write time and "not recoverable by a
    # script", so failing on it implied the one remedy the rule forbids, at the top of every
    # session, gating nothing (42 blocks, 0 contradicted labels, 2026-08-30). They are
    # printed as coverage every run and never as FAIL.
    status = "violations" if violations else "ok"
    return {
        "status": status,
        "files_examined": parsed,
        "guarded_class": GUARDED_CLASS,
        "violations": violations,
        "misalignments": misalignments,
        "unreadable": unreadable,
    }


def _report_reviewed(result: dict) -> None:
    """Reviewed coverage (v0.190.0): blocks a human read and left. Printed on OK and on FAIL,
    and a reason that repeats is named as a rule this check is missing."""
    reviewed = [m for m in result["misalignments"] if m.get("reviewed")]
    if not reviewed:
        return
    reasons: dict[str, int] = {}
    for m in reviewed:
        reasons[m.get("reviewed_reason", "")] = reasons.get(m.get("reviewed_reason", ""), 0) + 1
    print(
        f"  [reviewed coverage] {len(reviewed)} block(s) carry alignment_reviewed and are "
        "reported as coverage, not FAIL."
    )
    for reason, n in reasons.items():
        if n > 1:
            print(
                f"    {n} of them share one reason ({reason[:80]!r}): a reason that repeats "
                "is a rule this check is missing, not that many judgements."
            )


_COVERAGE_SHOWN = 6


def _report(result: dict) -> int:
    """Human-readable reporting. Split from main() to keep each branch legible."""
    status = result["status"]

    # NOT A PASS. Exiting 0 here would mean "I looked at nothing and everything is
    # fine", which check_empty_input_honesty.py exists to make impossible.
    if status == "no-canvas":
        print(
            "check_source_class_fidelity: NOT A PASS — no "
            f"{CANVAS_REL}/ under {result['canvas_dir']}. Nothing was examined.",
            file=sys.stderr,
        )
        return 1
    if status == "nothing-examined":
        print(
            "check_source_class_fidelity: NOT A PASS — "
            f"{result['files_found']} canvas file(s) found, none parsed. "
            "Nothing was examined.",
            file=sys.stderr,
        )
        for bad in result["unreadable"]:
            print(f"  unreadable: {bad['file']}: {bad['error']}", file=sys.stderr)
        return 1

    if status == "ok":
        reviewed_n = sum(1 for m in result["misalignments"] if m.get("reviewed"))
        tail = f"; {reviewed_n} block(s) of reviewed coverage" if reviewed_n else ""
        print(
            f"check_source_class_fidelity: OK — {result['files_examined']} canvas "
            f"file(s); no `{GUARDED_CLASS}` label contradicted by its own source text{tail}."
        )
        _print_coverage(result)
        _report_reviewed(result)
        return 0

    print(
        f"check_source_class_fidelity: FAIL — {len(result['violations'])} label(s) "
        f"contradicted by their own source, {len(result['misalignments'])} misaligned "
        f"block(s), across {result['files_examined']} canvas file(s)."
    )
    _print_coverage(result)
    _report_reviewed(result)
    _print_violations(result)
    return 1


def _print_coverage(result: dict) -> None:
    unreviewed = [m for m in result["misalignments"] if not m.get("reviewed")]
    if not unreviewed:
        return
    print(
        f"  COVERAGE: {len(unreviewed)} block(s) have unequal evidence_sources / "
        f"source_classes arrays, so fidelity could not be evaluated there. Not a defect: "
        f"the class is set at write time and the contract says it is not recoverable by a "
        f"script. Coverage rises as the canvas grows."
    )
    for m in unreviewed[:_COVERAGE_SHOWN]:
        print(f"    {m['file']} {m['id']}: {m['sources']} sources vs {m['classes']} classes")
    if len(unreviewed) > _COVERAGE_SHOWN:
        print(f"    ... and {len(unreviewed) - _COVERAGE_SHOWN} more")


def _print_violations(result: dict) -> None:
    for v in result["violations"]:
        print(f"  [{v['detector']}] {v['file']} {v['id']} idx{v['index']}")
        print(f"      {v['source']}")
        print(f"      why: {v['why']}")
    if result["violations"]:
        print(
            f"    `{GUARDED_CLASS}` means a human OUTSIDE this project said it.\n"
            "    check_source_independence.py counts distinct source_class values as\n"
            "    method diversity, so a mislabel here manufactures corroboration that\n"
            "    does not exist. Fix the class; do NOT delete the source.\n"
            "    Fixing a class may weaken a confidence value that rested on it —\n"
            "    re-derive it deliberately rather than leaving the number untouched."
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fail when a source_class contradicts the source text beside it.",
    )
    ap.add_argument("--root", default=".", help="project root containing .claude/canvas")
    # Accepted because sibling checks and session-start.sh disagree on the flag name.
    ap.add_argument("--project-dir", default=None, help="alias for --root")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    root = Path(args.project_dir or args.root).resolve()
    if not root.is_dir():
        print(f"check_source_class_fidelity: not a directory: {root}", file=sys.stderr)
        return 2

    result = evaluate(root)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ok" else 1

    return _report(result)


if __name__ == "__main__":
    sys.exit(main())
