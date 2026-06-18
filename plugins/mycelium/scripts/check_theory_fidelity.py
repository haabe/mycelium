#!/usr/bin/env python3
"""check_theory_fidelity.py — static guard for theory→mechanism mapping integrity.

The `/theory-fidelity` skill is the *semantic* audit (is a mechanism faithful to
what the theory actually claims?) — that needs an LLM + source-grounding and runs
on cadence. This guard is the *structural* double-loop: it runs every push and
catches the mechanizable subset of drift, so a renamed skill, a phantom gate
reference, or a name-only theory smuggled into the load-bearing tiers fails CI
the moment it lands — not at the next quarterly audit.

What it CAN catch (low false-positive, structural):
  A. Skill-reference resolution — every `/skill` token in theories.md Tier 1/2
     resolves to plugins/mycelium/skills/<name>/SKILL.md.
  B. Gate-number resolution — every `gate N` token resolves to a `### N.` in
     theory-gates.md.
  C. Engine/harness path resolution — every `engine|harness|orchestration/X.md`
     token resolves to a real file under plugins/mycelium/.
  D. Gate grounding — every gate section in theory-gates.md carries a `**Source**:`
     line (no gate ships without a named theory).
  E. No name-only theory — every Tier-1 section and Tier-2 row carries at least
     one resolvable mechanism token (the doc's own "citations without
     mechanism-mapping are theatre" rule, mechanized).

What it deliberately does NOT catch (irreducibly semantic — Layers 2/3, the
/theory-fidelity skill + ground-truthing): whether a mechanism is *faithful* vs
*distorted* (e.g. "Torres selects via ICE" — wrong, but the reference resolves);
citation truth (Lopopolo vs Shinn); numberless prose gate claims ("gate at
L1→L2"); cross-file count consistency. The guard shrinks the attack surface; it
does not replace the audit.

Usage:
    check_theory_fidelity.py [--root REPO_ROOT] [--json]

Exit codes:
    0 — no structural drift
    1 — at least one structural defect (CI gate)
    2 — setup error (theories.md or theory-gates.md missing)

Python stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

THEORIES_MD = "docs/theories.md"
GATES_MD = "plugins/mycelium/engine/theory-gates.md"
SKILLS_DIR = "plugins/mycelium/skills"

# A leading-slash skill token: `/name` or `/mycelium:name`. The negative
# look-behind keeps `canvas/landscape.yml` and `engine/x.md` (no leading slash)
# out — those are handled separately and by different existence domains.
SKILL_RE = re.compile(r"(?<![A-Za-z0-9_:])/(?:mycelium:)?([a-z][a-z0-9-]+)")
GATE_RE = re.compile(r"\bgate\s+(\d+)", re.IGNORECASE)
ENGINE_PATH_RE = re.compile(r"\b(engine|harness|orchestration)/([A-Za-z0-9_-]+\.md)\b")
GATE_HEADER_RE = re.compile(r"^### (\d+)\.\s", re.MULTILINE)
# A "mechanism pointer" for the name-only check (E): a concrete artifact of any
# kind — a file (canvas/schema/doc), a skill, a gate number, or a guardrail code
# (G-M2, G-P7, …). A/B/C still do real existence-resolution for skills/gates/
# engine-paths; E only asks "is there any mechanism pointer at all, or pure prose?"
FILENAME_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:md|ya?ml|json|py|sh)\b")
GUARDRAIL_RE = re.compile(r"\bG-[A-Z][A-Za-z0-9-]*\b")


def _section(text, start_marker, *end_markers):
    """Return the slice of `text` from start_marker to the first end_marker."""
    start = text.find(start_marker)
    if start == -1:
        return ""
    rest = text[start + len(start_marker):]
    end = len(rest)
    for m in end_markers:
        i = rest.find(m)
        if i != -1:
            end = min(end, i)
    return rest[:end]


def _gate_numbers_and_sources(gates_text):
    """Map gate number -> bool(has **Source**: line) from theory-gates.md."""
    headers = list(GATE_HEADER_RE.finditer(gates_text))
    out = {}
    for i, h in enumerate(headers):
        num = h.group(1)
        body_start = h.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(gates_text)
        body = gates_text[body_start:body_end]
        out[num] = "**Source**:" in body or "**Source:**" in body
    return out


def scan(root: Path):
    errors = []  # (check, detail)
    theories_path = root / THEORIES_MD
    gates_path = root / GATES_MD
    theories = theories_path.read_text(encoding="utf-8")
    gates = gates_path.read_text(encoding="utf-8")

    # Load-bearing tiers only: Tier 3 is citation-only by design (exempt).
    tier1 = _section(theories, "## Tier 1", "## Tier 2", "## Tier 3", "## See also")
    tier2 = _section(theories, "## Tier 2", "## Tier 3", "## See also")
    tier12 = tier1 + "\n" + tier2

    gate_sources = _gate_numbers_and_sources(gates)
    valid_gate_nums = set(gate_sources)

    # A. skill references resolve
    for name in sorted(set(SKILL_RE.findall(tier12))):
        if not (root / SKILLS_DIR / name / "SKILL.md").is_file():
            errors.append(("A:skill-ref", f"theories.md references `/{name}` — no plugins/mycelium/skills/{name}/SKILL.md"))

    # B. gate-number references resolve
    for num in sorted(set(GATE_RE.findall(tier12)), key=int):
        if num not in valid_gate_nums:
            errors.append(("B:gate-ref", f"theories.md references `gate {num}` — no `### {num}.` in theory-gates.md"))

    # C. engine/harness/orchestration doc paths resolve
    for sub, fname in sorted(set(ENGINE_PATH_RE.findall(tier12))):
        if not (root / "plugins/mycelium" / sub / fname).is_file():
            errors.append(("C:doc-path", f"theories.md references `{sub}/{fname}` — no plugins/mycelium/{sub}/{fname}"))

    # D. every gate carries a named theory Source
    for num in sorted(gate_sources, key=int):
        if not gate_sources[num]:
            errors.append(("D:gate-source", f"theory-gates.md gate {num} has no `**Source**:` line — gate shipped without a named theory"))

    # E. no name-only theory in the load-bearing tiers (≥1 resolvable mechanism token per unit)
    def has_mechanism(chunk):
        return bool(
            SKILL_RE.search(chunk)
            or GATE_RE.search(chunk)
            or ENGINE_PATH_RE.search(chunk)
            or FILENAME_RE.search(chunk)
            or GUARDRAIL_RE.search(chunk)
        )

    # Tier 1: ### sections
    for part in re.split(r"\n### ", tier1)[1:]:
        title = part.splitlines()[0].strip()
        if not has_mechanism(part):
            errors.append(("E:name-only", f"Tier-1 theory '{title}' has no resolvable mechanism token (skill/gate/engine-path) — name-only in a load-bearing tier"))
    # Tier 2: table rows (skip header + separator)
    for line in tier2.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.startswith("|---") or s.startswith("| Theory"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or not cells[0]:
            continue
        if not has_mechanism(line):
            errors.append(("E:name-only", f"Tier-2 theory '{cells[0]}' has no resolvable mechanism token — name-only in a load-bearing tier"))

    return {"errors": errors, "gates_checked": len(gate_sources)}


def main(argv=None):
    p = argparse.ArgumentParser(description="Guard the theory→mechanism mapping in docs/theories.md against structural drift.")
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]

    for rel in (THEORIES_MD, GATES_MD):
        if not (root / rel).is_file():
            print(f"error: missing {rel} under {root}", file=sys.stderr)
            return 2

    report = scan(root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Theory fidelity (structural): checked {report['gates_checked']} gates + theories.md Tier 1/2 references.")
        if report["errors"]:
            print(f"\nSTRUCTURAL DRIFT ({len(report['errors'])}):")
            for check, detail in report["errors"]:
                print(f"  [{check}] {detail}")
            print("\nNote: this guard checks structural integrity only. Semantic fidelity "
                  "(faithful vs distorted, citation truth) is the /theory-fidelity skill's job.")
        else:
            print("No structural theory-mapping drift.")

    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
