#!/usr/bin/env python3
"""mutation_sample.py — does a test suite fail when the mechanism it names is broken?

WHY (2026-09-10). `engine/feedback-loops.md` has listed "mutation testing score" as the Goodhart
counter-metric for test coverage since the table was written, and nothing computed it. The same
day a structural classifier put 97% of this repo's 1,396 pytest functions in the "runs production
code and asserts on its output" bin, and a hand read of 16 agreed. Shape is not adequacy: a test
can run the code and assert the one thing a broken mechanism still gets right. The first pass of
this script found exit codes on clean paths that no test asserted in four checks, an OR-predicate
whose branches were never exercised one at a time, and boundary comparisons (`<` vs `<=`) that no
fixture sat on.

WHAT IT DOES. For a sample of `scripts/check_*.py` modules that have a
`tests/python/test_<name>.py`, apply small single-site mutations to CODE tokens only (never
strings, comments or docstrings: those are equivalent mutants and inflate survivors), run that
module's tests, and count killed vs survived. Bytecode caching is disabled and `__pycache__`
cleared per mutant, because Python keys the cache on source mtime in seconds and size, and a same-
size mutant written and restored within one second runs the STALE bytecode and reads as a survivor
that is not one (measured: 52% -> 76% on the same sample once this was fixed).

WHAT A NUMBER MEANS. Killed/mutants over a random sample, seeded. It is a sample, not the suite;
f-string wording mutants still count and a few survivors are equivalent. Read the survivor list,
not the percentage: each survivor names a line whose behaviour no test constrains.

USAGE
    mutation_sample.py [--root DIR] [--modules N] [--mutants-per-module N] [--seed N] [--json]
    exit 0 always (report-only); exit 2 when nothing could be mutated (UNKNOWN, never a pass).
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

OPS: list[tuple[str, str]] = [
    (r"(?<![=!<>])==(?!=)", "!="),
    (r"!=", "=="),
    (r"(?<![<>=\-])<(?![<=])", "<="),
    (r"(?<![<>=\-])>(?![>=])", ">="),
    (r">=", "<"),
    (r"<=", ">"),
    (r"\breturn 1\b", "return 0"),
    (r"\breturn 0\b", "return 1"),
    (r"\band\b", "or"),
    (r"\bor\b", "and"),
    (r"\bnot\b", ""),
    (r"\bTrue\b", "False"),
    (r"\bFalse\b", "True"),
    (r"\+ 1\b", "- 1"),
]


def _string_spans(src: str) -> list[tuple[int, int, int]]:
    """(line, col_lo, col_hi) ranges covered by STRING/COMMENT/FSTRING tokens."""
    spans = []
    kinds = {tokenize.STRING, tokenize.COMMENT}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, name):
            kinds.add(getattr(tokenize, name))
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError) as exc:
        # spoken: without token spans every string would be a mutation site, so say so
        print(f"mutation-sample: could not tokenize a module ({exc}); string spans unknown, "
              "mutants in this module may include string text.")
        return spans
    for tok in toks:
        if tok.type in kinds:
            (r1, c1), (r2, c2) = tok.start, tok.end
            spans.extend((r, c1 if r == r1 else 0, c2 if r == r2 else 10**6)
                         for r in range(r1, r2 + 1))
    return spans


def mutation_sites(src: str) -> list[tuple[int, int, int, str]]:
    """Every (line_index, start, end, replacement) on a code token."""
    spans = _string_spans(src)

    def in_str(line: int, col: int) -> bool:
        return any(r == line and lo <= col < hi for r, lo, hi in spans)

    sites = []
    for i, line in enumerate(src.split("\n")):
        s = line.strip()
        if "print(" in line or "->" in line or s.startswith(("def ", "#")):
            continue
        for pat, rep in OPS:
            for m in re.finditer(pat, line):
                if in_str(i + 1, m.start()):
                    continue
                sites.append((i, m.start(), m.end(), rep))
    return sites


def run_tests(root: Path, test_path: Path, timeout: int = 120) -> int | None:
    """pytest exit code for one test file, bytecode disabled; None on timeout."""
    for d in (root / "plugins" / "mycelium" / "scripts" / "__pycache__",
              test_path.parent / "__pycache__"):
        shutil.rmtree(d, ignore_errors=True)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                            str(test_path)], cwd=root, capture_output=True, text=True,
                           timeout=timeout, env=env, check=False)
    except subprocess.TimeoutExpired:
        return None  # counted as a timeout by mutate_module and printed in the report
    return r.returncode


def mutate_module(  # noqa: PLR0913, PLR0917 — six named inputs read better than a config object
    root: Path, src_path: Path, test_path: Path, per_module: int,
    rng: random.Random, runner=run_tests,
) -> dict:
    """Mutate one module up to per_module times; restore it after every run."""
    src = src_path.read_text(encoding="utf-8")
    lines = src.split("\n")
    sites = mutation_sites(src)
    rng.shuffle(sites)
    chosen = sites[:per_module]
    killed, survived, timeouts = 0, [], 0
    backup = src_path.with_suffix(src_path.suffix + ".mutbak")
    for i, a, b, rep in chosen:
        mut = lines[:]
        mut[i] = lines[i][:a] + rep + lines[i][b:]
        shutil.copy(src_path, backup)
        src_path.write_text("\n".join(mut), encoding="utf-8")
        try:
            rc = runner(root, test_path)
        finally:
            shutil.move(backup, src_path)
        if rc is None:
            timeouts += 1
        elif rc == 0:
            survived.append({"line": i + 1, "orig": lines[i].strip()[:100],
                             "mutant": mut[i].strip()[:100]})
        else:
            killed += 1
    return {"module": src_path.name, "sites": len(sites), "mutants": len(chosen),
            "killed": killed, "survived": survived, "timeouts": timeouts}


def candidates(root: Path) -> list[tuple[Path, Path]]:
    out = []
    for f in sorted(glob.glob(str(root / "plugins" / "mycelium" / "scripts" / "check_*.py"))):
        p = Path(f)
        t = root / "tests" / "python" / f"test_{p.stem}.py"
        if t.exists():
            out.append((p, t))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mutation sample over the shipped checks.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--modules", type=int, default=12)
    ap.add_argument("--mutants-per-module", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260910)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    cands = candidates(root)
    if not cands:
        print(f"mutation-sample: UNKNOWN — no check_*.py with a matching test under {root}. "
              "Nothing was mutated, and this is not a pass.")
        return 2
    rng = random.Random(args.seed)  # noqa: S311 — sampling, not cryptography
    sample = rng.sample(cands, min(args.modules, len(cands)))
    results = [mutate_module(root, s, t, args.mutants_per_module, rng) for s, t in sample]
    tm = sum(r["mutants"] for r in results)
    tk = sum(r["killed"] for r in results)
    score = round(100 * tk / tm, 1) if tm else None
    if args.json:
        print(json.dumps({"modules": results, "mutants": tm, "killed": tk, "score": score},
                         indent=1))
        return 0 if tm else 2
    if not tm:
        print("mutation-sample: UNKNOWN — the sampled modules offered no mutation site. "
              "Not a pass.")
        return 2
    print(f"mutation-sample: {len(results)} module(s), {tm} mutant(s), {tk} killed, "
          f"score {score}% (seed {args.seed}).")
    print("  A survivor is a line whose behaviour no test constrains. Read the list, not the "
          "score;")
    print("  f-string wording and a few equivalent mutants are still counted.")
    for r in results:
        print(f"  {r['module']:<40} mutants {r['mutants']:>2} killed {r['killed']:>2} "
              f"survived {len(r['survived']):>2}")
        for s in r["survived"]:
            print(f"      L{s['line']}: {s['orig'][:60]}  ->  {s['mutant'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
