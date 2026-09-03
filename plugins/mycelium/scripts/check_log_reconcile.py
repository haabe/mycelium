#!/usr/bin/env python3
"""A dated event in the decision log whose canvas row was never written.

THIS SHIPS GREEN, AND THAT IS STATED FIRST because a check introduced with no
failing instance is the kind that quietly becomes noise. It is a REGRESSION GUARD
against two documented failures, not a discovery tool, and it found nothing on the
corpus that motivated it. Measured 2026-08-20 on the dogfood repo: BVSSH 8 dated
log events against 14 canvas rows, DORA 3 against 9, zero log-only in either, and
zero dangling canvas IDs across 253 cited. If it stays green for a long window,
narrow or retire it — that is this project's own rule for a guard with a near-zero
action rate (opp-048), and it applies to this file too.

THE FAILURE IT GUARDS, twice recorded.

  1. A BVSSH assessment was ORPHANED to the decision log and never reached
     `bvssh-health.yml#assessment_history`. `check_bvssh_reconcile.py` exists
     because of it.
  2. DORA, 2026-08-09: the measurement WAS taken and written into the metric
     fields, and `measurement_history` never gained the row. One file then carried
     THREE dates for one measurement — 2026-08-08 in the fields, 2026-08-02 in the
     top-level stamp, 2026-07-17 in the history — so every instrument asking "when
     was this measured" got a different answer depending on which it read.

Both are the same shape: **real work landing somewhere no instrument reads.** The
decision log is where it lands, which is why the only script that reads this file
for content reads it to detect exactly this.

DIRECTION MATTERS, and the asymmetry is inherited from check_bvssh_reconcile
rather than invented here. Log-without-canvas is the ORPHAN and fails. Canvas
-without-log is the HARMLESS direction and is reported as INFO: the canvas is the
source of truth, and failing on it would train people to stop writing the canvas.

WHY A REGISTRY RATHER THAN A THIRD BESPOKE CHECK. Two instances of one shape is
where a pattern earns a mechanism. Adding a class is one row. BVSSH is listed and
DEACTIVATED rather than omitted, because `check_bvssh_reconcile.py` already covers
it with special-case absent-input logic and is wired into `session-start.sh` — the
row documents the boundary instead of leaving a reader to wonder why the
motivating case is missing.

WHAT IT CANNOT DO. It matches DATES, not content. An entry can announce a
measurement and the canvas row can record a different number; nothing here would
notice. It also cannot tell a decision that legitimately belongs only in the log
(a rejected alternative, of which this corpus holds 159) from one that should have
been routed — so it only looks at classes explicitly registered below, never at
entries in general.

Exit codes:
    0  every registered class reconciles, or nothing to reconcile
    1  at least one dated log event has no canvas row
    2  the check itself could not run

Python stdlib only, so it runs in any consumer regardless of environment.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: (name, log-heading pattern capturing a date, canvas file, history key, active)
#:
#: `active=False` means another check already owns the class. The row stays so the
#: boundary is visible — an omitted class reads as an oversight, a deactivated one
#: reads as a decision.
RECONCILIATIONS = [
    (
        "DORA measurements",
        r"^###[^\n]*\bDORA\b[^\n]*?(\d{4}-\d{2}-\d{2})\s*$",
        "dora-metrics.yml",
        "measurement_history",
        True,
    ),
    (
        "BVSSH assessments",
        r"^###\s*BVSSH Assessment[^\n]*?(\d{4}-\d{2}-\d{2})\s*$",
        "bvssh-health.yml",
        "assessment_history",
        False,  # owned by check_bvssh_reconcile.py, wired into session-start.sh
    ),
]

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

#: CANVAS-TO-CANVAS reconciliations: (name, source file, source block, id field,
#: target file, target block, id field, states that count as a match).
#:
#: The list above reconciles the DECISION LOG against a canvas history. This one
#: reconciles two CANVASES against each other, because the same failure has the same
#: shape there: an event recorded on one surface and never on the other, with nothing
#: comparing them.
#:
#: MEASURED 2026-09-01 on the dogfood canvas. `archived-solutions.yml` held THREE killed
#: leaves — sol-047a, sol-047d, sol-047c-selectivity-half, all `archived_at: 2026-08-16`,
#: all `reason: failed-assumption`, each with an ice_score_at_archive, an evidence
#: snapshot and a decision-log ref — while `cycle-history.yml` reported 16 launched and
#: ZERO killed. The discard discipline was strong; only the cycle row was missing.
#:
#: WHY THAT IS WORTH A CHECK RATHER THAN A NOTE: a reader of cycle-history sees a 0%
#: discard rate, which this framework's own theory treats as a warning sign, and concludes
#: nothing is ever killed. An agent did exactly that on 2026-09-01 and wrote it up as a
#: finding before opening the archive.
CANVAS_RECONCILIATIONS = [
    (
        "killed leaves",
        "archived-solutions.yml", "archived", "leaf_id",
        "cycle-history.yml", "cycles", "leaf_id",
    ),
]


def _block_field_values(canvas: Path, block_key: str, field: str) -> set[str] | None:
    """Every `field:` value inside the `block_key:` block, or None if unreadable.

    Stdlib-only and block-scoped, matching the technique used by _history_dates above —
    this script family is required to run on a consumer with no third-party deps.
    """
    if not canvas.is_file():
        return None
    lines = canvas.read_text(encoding="utf-8", errors="replace").splitlines()
    # The `- ` prefix is NOT optional decoration: the first field of a YAML list item
    # sits on the dash line (`  - leaf_id: sol-047a`), so a pattern anchored on
    # whitespace alone silently matches nothing and the class reports "absent or empty"
    # — which is what it did on first run, over a file holding three entries.
    pattern = re.compile(
        rf"^\s*(?:-\s*)?{re.escape(field)}:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*$")
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{block_key}:"):
            indent = len(line) - len(line.lstrip())
            found = set()
            for nxt in lines[i + 1:]:
                stripped = nxt.strip()
                nxt_indent = len(nxt) - len(nxt.lstrip())
                # A LIST ITEM AT THE SAME INDENT AS ITS KEY IS STILL INSIDE THE BLOCK.
                # YAML permits `cycles:` at column 0 with `- cycle_id:` also at column 0, and
                # cycle-history.yml is written that way. Breaking on indent alone ended the
                # scan on the first item and returned an EMPTY SET — so every source id read
                # as missing from the target. Measured 2026-09-01: this reported three
                # archived leaves as orphaned when two of them had just been recorded.
                # A COMMENT IS NOT THE END OF THE BLOCK EITHER. Canvases carry comment
                # banners between list items, and a `#` at the key's indent is not a
                # sibling key. Measured the same day: a comment inserted above three new
                # cycles ended the scan before them, so they read as missing.
                if stripped.startswith("#"):
                    continue
                if stripped and nxt_indent <= indent and not stripped.startswith("- "):
                    break
                m = pattern.match(nxt)
                if m:
                    found.add(m.group(1))
            return found
    return None


# A reason must clear this to count. `x` or `n/a` must not buy an exemption --
# the same bar check_instrument_contract sets on its own waiver field.
_MIN_REASON_CHARS = 20

def _reconciliation_exemptions(canvas: Path, field: str) -> dict[str, str]:
    """ids whose entry declares, in a VALUE, that it has no counterpart and why.

    WHY THIS EXISTS (v0.175.0). A dogfood canvas recorded a deliberate omission —
    `sol-047c-selectivity-half` is archived and has no cycle row, because the schema forbids
    a product-leaf cycle with a zero ICE total and inventing one to silence a check is the
    corruption the founder's scoring ruling exists to prevent. The decision was right, it was
    reasoned, and it was written down. **In a YAML comment**, which no checker can read. So a
    correct decision produced a permanent exit 1, and a check that is always red is one people
    stop reading — the failure this script family keeps finding elsewhere.

    THIS IS THE `closed_with_discipline` SHAPE, borrowed deliberately: a null recorded properly
    is an ANSWER, not a gap. Both companions are required, for the same reason the closure trio
    requires all three — a bare marker would be a mute button, and the reason is the whole
    artifact.

        - leaf_id: sol-047c-selectivity-half
          reconciliation_exempt:
            reason: >-
              Half a leaf; only the parent carried an ICE score, and the schema forbids a
              zero-ICE product-leaf cycle.
            decided: 2026-08-31

    IT DOES NOT SILENCE THE ROW. The id is still printed every run, as EXEMPT with its reason,
    because the canvas comment this replaced asked for exactly that ("stays visible ... THAT IS
    THE HONEST STATE"). What changes is the exit status, not the visibility.
    """
    if not canvas.is_file():
        return {}
    text = canvas.read_text(encoding="utf-8", errors="replace")
    id_re = re.compile(
        rf"^\s*(?:-\s*)?{re.escape(field)}:\s*[\"']?([A-Za-z0-9_.-]+)[\"']?\s*$",
        re.MULTILINE)
    marks = [(m.group(1), m.end()) for m in id_re.finditer(text)]
    out: dict[str, str] = {}
    for i, (entry_id, pos) in enumerate(marks):
        chunk = text[pos:marks[i + 1][1] if i + 1 < len(marks) else len(text)]
        block = re.search(r"reconciliation_exempt:\s*\n(.*?)(?=\n\S|\Z)",
                          chunk, re.DOTALL)
        if not block:
            continue
        body = block.group(1)
        if not re.search(r"decided:\s*\S*\d{4}-\d{2}-\d{2}", body):
            continue
        reason_m = re.search(r"reason:\s*[>|]?-?\s*\n?(.*?)(?=\n\s*\w+:|\Z)",
                             body, re.DOTALL)
        reason = " ".join(reason_m.group(1).split()) if reason_m else ""
        if len(reason) >= _MIN_REASON_CHARS:
            out[entry_id] = reason
    return out


def _history_dates(canvas: Path, key: str) -> set[str] | None:
    """Dates inside the `key:` block of a canvas file, or None if unreadable.

    Deliberately not a YAML parse: stdlib-only so this runs in any consumer. Takes
    the block from `key:` to the next line indented at or below it, then collects
    every ISO date in it — the same block-boundary technique the rest of this
    script family uses.
    """
    if not canvas.is_file():
        return None
    lines = canvas.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            indent = len(line) - len(line.lstrip())
            block = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt)
            return set(_DATE.findall("\n".join(block)))
    return None


def analyse(root: Path) -> dict:
    log = root / ".claude" / "harness" / "decision-log.md"
    if not log.is_file():
        return {"error": f"no decision log at {log}"}
    text = log.read_text(encoding="utf-8", errors="replace")

    res: dict = {"orphans": [], "info": [], "skipped": [], "checked": 0}
    for name, pattern, fname, key, active in RECONCILIATIONS:
        if not active:
            res["skipped"].append((name, "owned by check_bvssh_reconcile.py"))
            continue
        log_dates = set(re.findall(pattern, text, re.MULTILINE))
        canvas_dates = _history_dates(root / ".claude" / "canvas" / fname, key)
        if canvas_dates is None:
            if log_dates:
                # Log events exist and the canvas history does not. That IS the orphan.
                res["orphans"].append((name, f"{fname}#{key} unreadable", sorted(log_dates)))
            else:
                res["skipped"].append((name, f"{fname}#{key} not present, and no log events"))
            continue
        res["checked"] += 1
        only_log = sorted(log_dates - canvas_dates)
        if only_log:
            res["orphans"].append((name, f"{fname}#{key}", only_log))
        only_canvas = sorted(canvas_dates - log_dates)
        if only_canvas:
            res["info"].append((name, len(only_canvas)))

    _reconcile_canvases(root / ".claude" / "canvas", res)
    return res


def _reconcile_canvases(canvas_dir: Path, res: dict) -> None:
    """Canvas-to-canvas pairs. Extracted to keep analyse() under the complexity limit."""
    for name, src, src_block, src_field, tgt, tgt_block, tgt_field in CANVAS_RECONCILIATIONS:
        src_ids = _block_field_values(canvas_dir / src, src_block, src_field)
        if not src_ids:
            res["skipped"].append((name, f"{src}#{src_block} absent or empty"))
            continue
        tgt_ids = _block_field_values(canvas_dir / tgt, tgt_block, tgt_field)
        if tgt_ids is None:
            res["orphans"].append((name, f"{tgt}#{tgt_block} unreadable", sorted(src_ids)))
            continue
        res["checked"] += 1
        exempt = _reconciliation_exemptions(canvas_dir / src, src_field)
        missing = sorted(src_ids - tgt_ids)
        claimed = [m for m in missing if m in exempt]
        for cid in claimed:
            res.setdefault("exempt", []).append((name, cid, exempt[cid]))
        missing = [m for m in missing if m not in exempt]
        if missing:
            res["orphans"].append(
                (name, f"in {src}#{src_block}, absent from {tgt}#{tgt_block}", missing))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile dated decision-log events with canvas history rows.")
    ap.add_argument("--root", default=".", help="project root containing .claude/")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    res = analyse(root)
    if "error" in res:
        # UNKNOWN, never clean. A check that cannot run must not report a pass.
        print(f"UNKNOWN: {res['error']}", file=sys.stderr)
        return 2

    for name, where, dates in res["orphans"]:
        # The source is named by `where` itself for canvas-to-canvas pairs, which already
        # read "in X, absent from Y". Only the log-to-canvas rows need the prefix.
        lead = "recorded" if where.startswith("in ") else "dated in the decision log, absent from"
        print(f"\nORPHANED — {name}: {lead} {where}")
        for d in dates:
            print(f"  {d}")
        print("  The work was done and the recording of it was not. Route it to the canvas;")
        print("  logging a finding is not the same as filing it.")

    for name, n in res["info"]:
        print(f"INFO — {name}: {n} canvas row(s) with no log entry. Not a failure.")
        print("  The canvas is the source of truth, and failing this direction would")
        print("  train people to stop writing it.")

    for name, cid, reason in res.get("exempt", []):
        # PRINTED EVERY RUN, DELIBERATELY. The canvas comment this mechanism replaced asked for
        # exactly this ("stays visible ... THAT IS THE HONEST STATE"). An exemption changes the
        # exit status, never the visibility — a reason nobody re-reads is how an exemption rots
        # into a mute button.
        print(f"EXEMPT — {name}: {cid}")
        print(f"  reason (declared in the canvas, dated): {reason}")

    for name, why in res["skipped"]:
        print(f"skip: {name} — {why}")

    if not res["orphans"]:
        print(f"\nLog reconcile: OK — {res['checked']} registered class(es), "
              "no orphaned events.")
        print("This is a REGRESSION GUARD and it ships green: it found nothing on")
        print("the corpus that motivated it. If it stays green over a long window,")
        print("narrow or retire it rather than leaving it running — a guard with a")
        print("near-zero action rate trains its reader to skim.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
