#!/usr/bin/env python3
"""Does each test actually exercise production code, or only itself?

THE GAP THIS CLOSES. `check_wiring.py` proves a shipped mechanism has a caller.
`check_negative_control.py` proves a guard is able to fail. Neither asks the
question that sits between them: **when the test runs, does real production code
run?** A test can import nothing, assert a tautology, or mock away the very thing
it names, and still be green, covered, and counted.

Every failure this gate exists for is on record:
  * `verify_citations.py` shipped with passing tests and a matcher that matched
    0% of real citations for ~2.5 months. The tests exercised the function; no
    test fed it a real citation.
  * `hooks_no_errors` returned True on an empty state directory — passing hardest
    exactly when the hook layer was dead.
  * A dogfood evaluator fallback answered any unrecognised criterion by checking
    whether its own name appeared in a file the agent writes.
  * From a sibling project's corrections log, the same shape in another stack:
    "visualization rendered blank canvas — no automated test caught the missing
    wiring because unit tests mock the data sources."

Coverage percentage cannot see any of this. Coverage measures which lines ran,
never whether the assertion that followed them meant anything.

DESIGN RULES, each learned from a gate that went stale:
  * **Scope is derived.** Every file matching a test naming convention anywhere
    under --root is in scope. There is no list of files to keep up to date,
    because a list is stale the moment someone adds the next test.
  * **Unknown is not a pass.** A test file in a language this gate cannot parse
    is reported as UNCHECKED with a count, never silently skipped. A gate that
    quietly narrows its own scope reports health it did not measure.
  * **Exemptions are named and few.** Each carries a reason, and "it is hard to
    check" is not one.

Exit 0 clean, 1 on findings, 2 on usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from pathlib import Path

# These scripts are run three ways: as `python3 .../scripts/x.py` from any cwd,
# imported as a package, and loaded by file path from tests. Only the first puts
# this directory on sys.path, so put it there explicitly before the sibling
# import — the alternative is a module that works until the way it is loaded
# changes, which is how this landed as a test-collection error the first time.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import _scan_lib
except ImportError:  # invoked as a script, or loaded by file path
    import _scan_lib

# ---------------------------------------------------------------- scope

# A file is a test because of its NAME, never merely because of its directory.
# `**/tests/**/*.sh` swept in `tests/validate-template.sh` — the 1400-line
# structural validator that the bash suite EXERCISES — and reported the system
# under test as a test that tests nothing. Directory membership says where a file
# lives; the naming convention says what it is.
TEST_PATTERNS = (
    "**/test_*.py", "**/*_test.py",
    "**/test_*.sh", "**/*_test.sh",
    "**/*.test.ts", "**/*.test.tsx", "**/*.test.js", "**/*.test.jsx",
    "**/*.spec.ts", "**/*.spec.tsx", "**/*.spec.js", "**/*.spec.jsx",
)

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "fixtures", ".fixtures", "results",
}

# Files that are test-shaped but are not tests. Each needs a reason that is about
# the file's PURPOSE, never about the difficulty of checking it.
EXEMPT = {
    "conftest.py": "pytest fixture module — defines fixtures, asserts nothing",
    "__init__.py": "package marker",
}

# Shorter than this and a "production name" is a fragment that matches everywhere
# (`os`, `re`, `run`), producing reach hits that mean nothing.
MIN_PRODUCTION_NAME_LEN = 4

# How many UNCHECKED files to list before summarising. The count is always
# printed in full — only the listing is capped, and the remainder is stated.
MAX_LISTED = 20

LANG_BY_SUFFIX = {
    ".py": "python", ".sh": "bash", ".bash": "bash",
    ".ts": "js", ".tsx": "js", ".js": "js", ".jsx": "js",
}

# ---------------------------------------------------------------- tautologies

# Assertions that are true regardless of the system under test. These are the
# literal forms seen in the wild; the list is a floor, and Rule 1 (real code must
# be reachable) is what catches the shapes no pattern anticipates.
# A LIST of independent patterns, not one alternation. The first version wrapped
# every branch in a single outer group so that `\1` inside a branch referred to
# that still-open group, and re.compile raised "cannot refer to an open group" at
# import time. Separate patterns also let each finding say what is wrong rather
# than echoing an opaque match.
# Tautology patterns are LANGUAGE-SCOPED. Applying the shell forms to Python
# files made this gate flag its own test suite: the fixture string `[ 1 = 1 ]`,
# which exists precisely to prove the shell rule bites, was read as a real
# tautology inside a .py file. A detector that fires on its own test data is
# telling you the rule is untyped, not that the data is wrong.
_PY_TAUTOLOGIES = (
    (re.compile(r"^\s*assert\s+True\s*(?:#.*)?$", re.MULTILINE),
     "`assert True` is true whatever the code does"),
    (re.compile(r"^\s*assert\s+(\d+)\s*==\s*\1\s*$", re.MULTILINE),
     "asserts a number equals itself"),
    (re.compile(r"assertTrue\s*\(\s*True\s*\)"),
     "`assertTrue(True)` cannot fail"),
    (re.compile(r"assertEqual\s*\(\s*(\d+)\s*,\s*\1\s*\)"),
     "`assertEqual(n, n)` cannot fail"),
)
_SH_TAUTOLOGIES = (
    (re.compile(r"\[\s*(\d+)\s*(?:=|-eq)\s*\1\s*\]"),
     "shell test compares a number with itself"),
    (re.compile(r"\[\s*([\'\"]?)([A-Za-z0-9_]+)\1\s*=\s*\1\2\1\s*\]"),
     "shell test compares a literal with itself"),
)
_JS_TAUTOLOGIES = (
    (re.compile(r"expect\s*\(\s*(true|1)\s*\)\s*\.\s*toBe\s*\(\s*\1\s*\)"),
     "`expect(x).toBe(x)` on a literal cannot fail"),
)
TAUTOLOGIES_BY_LANG = {
    "python": _PY_TAUTOLOGIES,
    "bash": _SH_TAUTOLOGIES,
    "js": _JS_TAUTOLOGIES,
}

PLACEHOLDER_RE = re.compile(
    r"^\s*(?:#|//)\s*(?:simulate|stub|placeholder|fake|pretend|todo:?\s*test)\b",
    re.IGNORECASE | re.MULTILINE,
)


class Finding:
    def __init__(self, path: Path, rule: str, detail: str, line: int | None = None):
        self.path, self.rule, self.detail, self.line = path, rule, detail, line

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else str(self.path)
        return f"  [{self.rule}] {where}\n      {self.detail}"


def _iter_test_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    ignored = _scan_lib.ignored_paths(root)
    for pattern in TEST_PATTERNS:
        for f in root.glob(pattern):
            if not f.is_file():
                continue
            if any(part in SKIP_DIRS for part in f.parts):
                continue
            if _scan_lib.is_ignored(f, ignored):
                continue
            if f.name in EXEMPT:
                continue
            # Test INFRASTRUCTURE is not a test. `tests/bash/_assert.sh` is the
            # assertion helper, and `tests/validate-template.sh` is the validator
            # the whole bash suite exercises — scanning either as a test produced
            # findings about files that were never meant to assert anything.
            if _is_test_infrastructure(f) and not TEST_NAME_RE.match(f.name):
                continue
            seen.add(f)
    return sorted(seen)


TEST_NAME_RE = re.compile(
    r"^(?:test_.*|.*_test)\.(?:py|sh)$|^.*\.(?:test|spec)\.(?:tsx?|jsx?)$",
)


def _in_test_tree(path: Path) -> bool:
    return any(p in {"tests", "test", "__tests__", "spec"} for p in path.parts)


def _is_test_infrastructure(path: Path) -> bool:
    """Test helpers and runners: real code, but neither a test nor the system under test.

    Identified by name AND location, which took two corrections to get right:

    1. The first version treated everything under a `tests/` directory as
       non-production. This repo's structural validator lives at
       `tests/validate-template.sh` and IS what the 51 bash tests exercise, so
       all 51 were reported as touching no production code — 44 false positives.
       A gate that cries wolf gets switched off, and is then worth less than none.
    2. The second version treated any leading-underscore file as a helper.
       `plugins/mycelium/scripts/_manifest_lib.py` is shipped production whose
       name merely signals "internal", so its two tests were flagged. The
       underscore convention only means "helper" INSIDE a test tree.
    """
    name = path.name
    if TEST_NAME_RE.match(name):
        return True
    if _in_test_tree(path):
        return name.startswith("_") or name in {"conftest.py", "run.sh", "runner.sh"}
    return False


def _strip_comments(text: str) -> str:
    """Remove comment-only content so prose cannot satisfy a code-reach check.

    Deliberately crude: full-line comments and trailing `#`/`//` runs. A test that
    merely *names* a production module in a docstring has not called it.
    """
    out = []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith(("#", "//", "*", '"""', "'''")):
            continue
        out.append(re.sub(r"\s+(?:#|//)\s.*$", "", line))
    return "\n".join(out)


def _reaches_production(text: str, prod: set[str]) -> set[str]:
    """Production names referenced from non-comment code, by ANY mechanism.

    One check instead of one per import style, because the mechanisms are
    open-ended and enumerating them is how a gate goes stale. All of these count,
    and all appear in this repo's own suite:
        import check_wiring                       — static import
        spec_from_file_location(..., "x.py")      — dynamic import
        subprocess.run(["python3", "parse_manifest.py"])  — subprocess
        (REPO / "plugins" / ... / "SKILL.md").read_text() — shipped-artifact read
        bash "$SRC/tests/validate-template.sh"    — sourced shell script
    """
    code = _strip_comments(text)
    hits = set()
    for name in prod:
        if len(name) < MIN_PRODUCTION_NAME_LEN:
            continue
        # Lookbehind guards only against WORD characters, so `parse_manifest` does
        # not count as a reference to `manifest`. It must NOT exclude `/`, `.` or
        # `-`: the commonest reference in a shell test is a path,
        # `"$REPO_ROOT/tests/validate-template.sh"`, where the name is preceded by
        # a slash. The stricter first version rejected exactly those and put 45
        # false positives back on the board.
        if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", code):
            hits.add(name)
    return hits


def _production_modules(root: Path) -> set[str]:
    """Names a test could reference to reach code that is not itself test scaffolding.

    Derived from the tree, never configured: anything that is neither a test file
    nor test infrastructure counts as production, wherever it lives. A new script
    is recognised the moment it exists, which is the property a hand-kept list
    always loses.
    """
    names: set[str] = set()
    # SAME IGNORE FILTER AS THE TEST WALK (code review 2026-08-03). v0.73.1 wired
    # `_scan_lib` into `_iter_test_files` and missed this, the module's SECOND
    # tree walk — so names harvested from git-ignored vendored trees still counted
    # as "production reach". Reproduced with a control: a test whose only
    # reference is a string matching a file inside an ignored tree is NOT flagged,
    # and IS flagged once that tree is removed. In the dogfood consumer, which
    # vendors two third-party repos, every common stem (`runner`, `config`,
    # `index`) is harvested from somebody else's code and silences real findings.
    ignored = _scan_lib.ignored_paths(root)
    # Documents are shipped artefacts, not just code. Mycelium delivers 58 skills
    # as SKILL.md, its contract as engine/*.md, and its schemas as JSON — a test
    # asserting on that content exercises the product as surely as one importing
    # a module. Restricting production to .py/.sh flagged the ai-system-card test,
    # whose whole job is to hold shipped documentation to its contract.
    for suffix in ("*.py", "*.sh", "*.md", "*.yml", "*.yaml", "*.json"):
        for f in root.glob(f"**/{suffix}"):
            if any(p in SKIP_DIRS for p in f.parts):
                continue
            if _scan_lib.is_ignored(f, ignored):
                continue
            if _is_test_infrastructure(f):
                continue
            names.add(f.stem)
            names.add(f.name)
    return names


def _check_python(path: Path, text: str, prod: set[str]) -> list[Finding]:
    out: list[Finding] = []
    touched = _reaches_production(text, prod)
    if not touched:
        out.append(Finding(
            path, "no-production-reach",
            "references nothing this repo ships from non-comment code, by import, "
            "dynamic import, subprocess or file read — so no production code runs.",
        ))
        return out
    # A test that patches every production module it touches executes none of it.
    patched = {m.split(".")[0] for m in re.findall(r"patch(?:\.object)?\(\s*['\"]?([\w.]+)", text)}
    if patched and touched <= patched:
        out.append(Finding(
            path, "fully-mocked",
            f"every production module it touches ({sorted(touched)}) is patched, so "
            "the test exercises mocks only. This is the shape that ships a blank "
            "screen with a green suite.",
        ))
    return out


def _check_bash(path: Path, text: str, prod: set[str]) -> list[Finding]:
    if _reaches_production(text, prod):
        return []
    return [Finding(
        path, "no-production-reach",
        "never sources or invokes a script this repo ships.",
    )]


def _check_js(path: Path, text: str, prod: set[str]) -> list[Finding]:
    code = _strip_comments(text)
    local = re.findall(r"""(?:from|require\()\s*['\"](\.[^'\"]+)['\"]""", code)
    if local or _reaches_production(text, prod):
        return []
    return [Finding(
        path, "no-production-reach",
        "imports nothing from the local source tree, so no production code runs.",
    )]


CHECKERS = {"python": _check_python, "bash": _check_bash, "js": _check_js}


def check_file(path: Path, prod: set[str]) -> tuple[list[Finding], bool]:
    """Findings for one test file, plus whether it could be checked at all."""
    lang = LANG_BY_SUFFIX.get(path.suffix)
    if lang is None or lang not in CHECKERS:
        return [], False
    try:
        text = path.read_text(errors="replace")
    except OSError as exc:
        return [Finding(path, "unreadable", f"cannot read: {exc}")], True

    reaches = _reaches_production(text, prod)
    findings = list(CHECKERS[lang](path, text, prod))

    for pattern, why in TAUTOLOGIES_BY_LANG.get(lang, ()):
        for m in pattern.finditer(text):
            line = text[: m.start()].count("\n") + 1
            findings.append(Finding(
                path, "tautology", f"{why}: {m.group(0).strip()!r}", line,
            ))
    # A placeholder marker is only damning when nothing real runs. `# Simulate`
    # most often narrates FIXTURE construction ("simulate a session where X was
    # not read") in a test that then calls production for real — that is good
    # testing, and flagging it taught the gate to cry wolf. Reported only for a
    # file that also reaches no production code, where the two together mean the
    # test is scaffolding all the way down.
    if not reaches:
        for m in PLACEHOLDER_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            findings.append(Finding(
                path, "placeholder",
                f"placeholder marker in a test that reaches no production code: "
                f"{m.group(0).strip()!r}", line,
            ))
    return findings, True


def _report_unchecked(unchecked: list[Path], root: Path) -> None:
    """Reported, never silent: a narrowed scope must be visible in the output, or
    the gate claims coverage it does not have."""
    if not unchecked:
        return
    print(f"\n  UNCHECKED ({len(unchecked)} file(s) in an unsupported language):")
    for u in unchecked[:MAX_LISTED]:
        print(f"    {u.relative_to(root)}")
    if len(unchecked) > MAX_LISTED:
        print(f"    ... and {len(unchecked) - MAX_LISTED} more")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="repo root to scan")
    ap.add_argument("--quiet", action="store_true", help="only print findings")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: --root {root} is not a directory", file=sys.stderr)
        return 2

    tests = _iter_test_files(root)
    if not tests:
        # No tests is not a pass. A repo with no test files cannot have authentic
        # ones, and reporting "clean" here is the silence this gate is against.
        print(f"check_test_authenticity: no test files found under {root}.")
        print("  Not treated as a pass — nothing was verified. If this repo has")
        print("  tests under a convention this gate does not recognise, add the")
        print("  pattern to TEST_PATTERNS rather than accepting a quiet zero.")
        return 1

    prod = _production_modules(root)
    findings: list[Finding] = []
    unchecked: list[Path] = []
    for t in tests:
        got, was_checked = check_file(t, prod)
        findings.extend(got)
        if not was_checked:
            unchecked.append(t)

    if not args.quiet:
        print(f"check_test_authenticity: {len(tests)} test file(s) under {root}")
        print(f"  languages checked: {sorted(CHECKERS)}")
        print(f"  production names derived: {len(prod)}")

    _report_unchecked(unchecked, root)

    if findings:
        print(f"\nFAIL: {len(findings)} authenticity finding(s):\n")
        for f in findings:
            with contextlib.suppress(ValueError):
                f.path = f.path.relative_to(root)
            print(f)
        print("\nA test that imports no production code, asserts a tautology, or")
        print("mocks away everything it names is indistinguishable from no test.")
        print("Coverage cannot see this: it measures which lines ran, never")
        print("whether the assertion after them meant anything.")
        return 1

    if not args.quiet:
        print("\nPASS: every checked test reaches production code and asserts "
              "something falsifiable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
