#!/usr/bin/env python3
"""check_published_records.py — a published page whose source died with the session.

THE GAP (i-productified dogfood, 2026-08-24). Mycelium's model of a shareable output was **a local
file a human hands over**. A framework-wide search for `outputs/`, `published_at`, `artifact_url`,
`hosted_at` and `permalink` returned nothing, so an agent publishing to a persistent address had to
invent where the source lives, how the address is recorded, and how an update finds it again.

MEASURED COST, ONE SESSION: three artifacts published; addresses recorded only in prose inside long
canvas entries and only because the user asked; sources left in session scratch. Had the session
ended: sources gone, addresses greppable only from prose, no update path, and a 20-minute external
pull lost with them.

WHAT THIS ASSERTS, and it is deliberately small. For every `published:` record on a canvas entry:
  * an `address` is present and URL-shaped — with no address the page cannot be updated, only
    replaced
  * a `source` is named AND STILL EXISTS ON DISK — the scratch-wipe case, and the one that actually
    happened
  * `published_at` is present — an undated record cannot be reasoned about later

**WHAT IT CANNOT DO, STATED HERE SO A GREEN IS NEVER READ AS COVERAGE.** It cannot detect a publish
that recorded NOTHING. The render fleet is read-only and need not touch the canvas, so there is no
producer to gate — an agent that publishes and writes no record leaves this nothing to fail on.
**That is the `gates_fired` shape**: a field fully specified, with no mechanism writing it. It
covers the diligent case only, and the convention in `engine/render-conventions.md` is what asks for
the record in the first place.

ABSENT-INPUT DISCIPLINE (anti-pattern #9)
  * No canvas dir, or a canvas dir holding no `.yml` at all -> exit 2, LOUD. Both are a broken
    tree or a wrong --project-dir, and neither is "this project publishes nothing".
  * Unparseable canvas file  -> skipped and NAMED, never silently treated as empty.
  * No `published:` records  -> exit 0 with `no-published-records`, reported as N/A. "Nothing has
    been published" and "everything published is recorded" are different facts.

Exit codes:
    0 — every published record carries an address, a live source, and a date (or nothing to audit)
    1 — a published record is missing one of them
    2 — argument/input error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is framework-wide
    print("check_published_records: PyYAML is required", file=sys.stderr)
    sys.exit(2)

URLISH = re.compile(r"^[a-z][a-z0-9+.-]*://\S+$", re.IGNORECASE)


def _walk(node, path=""):
    """Yield every `published:` list found anywhere in a canvas document."""
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else str(key)
            if key == "published" and isinstance(val, list):
                yield here, val
            else:
                yield from _walk(val, here)
    elif isinstance(node, list):
        for i, val in enumerate(node):
            yield from _walk(val, f"{path}[{i}]")


def audit(project_dir: Path):
    """Return (violations, records, skipped) or None when the canvas dir is absent."""
    canvas = project_dir / ".claude" / "canvas"
    if not canvas.is_dir():
        return None
    files = sorted(canvas.glob("*.yml"))
    if not files:
        # A canvas DIRECTORY with no canvas FILES is a broken tree or a wrong
        # --project-dir, not a project that happens to publish nothing. The two
        # are different facts and collapsing them is how a check reads green
        # forever over an empty repository (check_empty_input_honesty.py).
        return None
    violations, records, skipped = [], 0, []
    for path in files:
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            # NAMED, never silent: an unparseable canvas that reads as "no records"
            # is the fail-open shape this project audits everywhere else.
            skipped.append(f"{path.name}: {str(exc)[:70]}")
            continue
        for where, entries in _walk(doc):
            for i, rec in enumerate(entries):
                records += 1
                violations.extend(
                    {"file": path.name, "at": f"{where}[{i}]", "problem": problem}
                    for problem in _classify(rec, project_dir)
                )
    return violations, records, skipped


def _classify(rec, project_dir: Path):
    """Every problem with one record. A list, because one record can carry several."""
    if not isinstance(rec, dict):
        return ["not a mapping — a published record needs address, source and published_at"]
    out = []
    address = str(rec.get("address") or "").strip()
    if not address:
        out.append("no `address` — the page cannot be updated, only replaced")
    elif not URLISH.match(address):
        out.append(f"`address` is not URL-shaped: {address[:60]!r}")
    source = str(rec.get("source") or "").strip()
    if not source:
        out.append("no `source` — nothing survives the session to republish from")
    elif not (project_dir / source).exists():
        out.append(f"`source` recorded but missing on disk: {source}")
    if not str(rec.get("published_at") or "").strip():
        out.append("no `published_at` — an undated record cannot be reasoned about later")
    return out


def main(argv=None) -> int:
    # argv is a parameter, not sys.argv, so the tests can drive every output
    # path in-process. A suite that can only shell out reports 0% coverage of
    # a file it fully exercises — which is how this file first met the
    # per-file coverage floor.
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", "--root", dest="project_dir", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    result = audit(project_dir)
    if result is None:
        msg = (f"cannot audit: no .claude/canvas under {project_dir}, or it holds no canvas "
               f"files at all. Either is a broken tree or a wrong --project-dir, NOT a project "
               f"that publishes nothing. NOTHING WAS AUDITED — this is not a pass.")
        if args.json:
            print(json.dumps({"status": "precondition-failed", "reason": msg}))
        else:
            print(f"check_published_records: ERROR — {msg}", file=sys.stderr)
        return 2

    violations, records, skipped = result
    if records == 0:
        msg = ("no-published-records — no canvas entry claims a published output. N/A, not a pass "
               "over a population. NOTE: this check cannot see a publish that recorded nothing.")
        print(json.dumps({"status": "n/a", "reason": msg, "skipped": skipped}) if args.json
              else f"check_published_records: N/A — {msg}")
        return 0

    if args.json:
        print(json.dumps({
            "status": "violations" if violations else "ok",
            "published_violations": violations,
            "records": records,
            "skipped_unparseable": skipped,
        }, indent=2))
        return 1 if violations else 0

    for s in skipped:
        print(f"  SKIPPED (unparseable): {s}", file=sys.stderr)
    if violations:
        print(f"check_published_records: FAIL — {len(violations)} problem(s) across {records} "
              f"published record(s).")
        for v in violations:
            print(f"    {v['file']}:{v['at']} — {v['problem']}")
        print("  A publish is finished when a durable source, an address and a date all exist.\n"
              "  See engine/render-conventions.md § Published output. Updating means republishing\n"
              "  to the address ALREADY RECORDED — a new source path mints a new address, and\n"
              "  leaves two live copies with nothing raised.")
    else:
        print(f"check_published_records: OK — {records} published record(s), all with a live "
              f"source, an address and a date.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
