#!/usr/bin/env python3
"""check_citations.py — surface the project's do-not-cite register at the moment a claim lands.

THE FAILURE THIS EXISTS FOR, measured twice in one day (2026-09-01, dogfood):
  1. A "2026 DORA" citation was written into two canvas files without the register being read.
  2. Hours later the register's NARROW entry ("no DORA 2026 State of DevOps report") was
     PARAPHRASED into "no 2026 DORA report" and acted on, rewriting four surfaces that were
     already correct.
The rule existed, was right, and was not consulted at the moment of use. Both directions of the
same defect: not read, then read and broadened.

WHY THIS IS NOT ANOTHER LEXICAL GUARD. `absence_claim_guard.py` matches a PROSE SIGNATURE and was
measured by a consumer at 29 lifetime fires, 16 in one day, and zero of that day's four confirmed
errors caught. This check matches a CURATED LIST of specific strings a human wrote down. Its
precision is the register's precision; it cannot fire on a claim nobody has ruled on, and it
cannot be improved by tuning a regex — only by someone adding an entry.

WHAT IT PRINTS IS THE ENTRY VERBATIM, never a summary. Failure 2 above happened inside a
paraphrase, so the one thing this must not do is paraphrase.

Exit 0 always: this reports, it never gates. A register is a reading aid, and a citation that
looks wrong is sometimes right — which is precisely what failure 2 established.
"""
import argparse
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit(0)   # no yaml, no opinion — the validator's own import guard owns that error

# An occurrence sitting inside a correction is the record of the rule being APPLIED, not broken.
# Without this the check fires on its own register and on every note explaining a past fix —
# measured: 12 such lines in the dogfood canvas on the day the register was written.
_ANNOTATED = re.compile(
    r"CORRECTED|WITHDRAWN|RE-CORRECTED|do-not-cite|DO NOT CITE|MISATTRIB|CONFABULAT|"
    r"debunk|register|verbatim|NO PRIMARY|does not exist|no such",
    re.IGNORECASE)


def _annotated_block(lines, idx, lookback=12):
    """Is this line inside a block that already annotates the claim as ruled-on?

    Walks back to the start of the current indented prose block. A blank line or a line at lower
    indentation ends it — that is the same block boundary YAML itself uses.
    """
    if _ANNOTATED.search(lines[idx]):
        return True
    indent = len(lines[idx]) - len(lines[idx].lstrip())
    for back in range(1, lookback + 1):
        j = idx - back
        if j < 0:
            break
        prev = lines[j]
        if not prev.strip():
            break
        if len(prev) - len(prev.lstrip()) < indent and prev.strip().endswith((":", ">-", "|")):
            return bool(_ANNOTATED.search(prev))
        if _ANNOTATED.search(prev):
            return True
    return False


def load_register(project_dir):
    path = pathlib.Path(project_dir) / ".claude" / "harness" / "do-not-cite.yml"
    if not path.is_file():
        return None, path
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        # A MALFORMED REGISTER IS NOT AN ABSENT ONE, and swallowing the difference would mean a
        # typo silently disables every rule in the file while the check still reads green. The
        # marker is returned so both callers can say so out loud.
        return f"unreadable: {exc}", path
    entries = doc.get("entries")
    return (entries if isinstance(entries, list) else None), path


def scan(project_dir):
    """Return (findings, files_scanned, entries_loaded). Empty register => refuses to report."""
    entries, _ = load_register(project_dir)
    if isinstance(entries, str):
        return [("<register>", 0, {"verdict": "UNREADABLE", "verbatim": entries}, "")], 0, -1
    if not entries:
        return [], 0, 0

    targets = sorted((pathlib.Path(project_dir) / ".claude" / "canvas").glob("*.yml"))
    findings, scanned = [], 0
    for path in targets:
        try:
            lines = path.read_text(encoding="utf-8").split("\n")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        for num, line in enumerate(lines, 1):
            # BLOCK-level annotation, not line-level. YAML folds prose across many lines, so the
            # "CORRECTED" marker usually sits several lines above the token it explains. Measured
            # 2026-09-01: line-level matching produced 3 false positives out of 6 findings, every
            # one of them inside a correction block whose marker was 1-5 lines up. The false
            # positives named the missing convention: the unit is the block, not the line.
            if _annotated_block(lines, num - 1):
                continue
            for entry in entries:
                for token in entry.get("match") or []:
                    if token.lower() in line.lower():
                        findings.append((path.name, num, entry, token))
                        break
    return findings, scanned, len(entries)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", "--root", dest="project_dir", default=".")
    args = ap.parse_args()

    findings, scanned, entries = scan(args.project_dir)
    print("Do-not-cite register scan")
    print("=" * 60)
    if entries == -1:
        print("  A register EXISTS at .claude/harness/do-not-cite.yml and COULD NOT BE PARSED.")
        print(f"  {findings[0][2]['verbatim']}")
        print("  Every rule in it is currently inert. This is louder than an absent register,")
        print("  because someone believed these rules were live.")
        return 1
    if not entries:
        # EMPTY INPUT REFUSES rather than passing. A clean result over nothing is the false
        # green this repo keeps removing.
        print("  No register at .claude/harness/do-not-cite.yml, or it holds no entries.")
        print("  NOTHING WAS CHECKED. This is not a pass — a green result over an empty")
        print("  population is the one answer that is never true.")
        # EXIT 1, and this is why it is NOT in the blocking pre-push gate set: that hook treats
        # any non-zero as failure, so a project which has simply never written a register would be
        # blocked from pushing. Its automatic reader is validate_canvas, which emits this as a
        # WARN-tier finding and never fails. Refusing here keeps the standalone contract honest
        # without making an advisory reporter into a gate.
        return 1
    print(f"  {entries} register entrie(s) against {scanned} canvas file(s); "
          f"{len(findings)} unannotated occurrence(s).")
    if not findings:
        print("\n  No unannotated occurrence of a ruled-on claim. This is NOT 'every citation is\n"
              "  sound' — it is 'none appears that someone has already ruled against'.")
        return 0
    print()
    for name, num, entry, token in findings:
        print(f"  {name}:{num} matched \"{token}\"  [{entry.get('verdict', '?')}]")
        print(f"      {' '.join((entry.get('verbatim') or '').split())}")
        print()
    print("  Quote the entry, do not paraphrase it — a paraphrase is where breadth gets added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
