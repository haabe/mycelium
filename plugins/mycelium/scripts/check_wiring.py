#!/usr/bin/env python3
"""check_wiring.py — guard against mechanisms that exist but are never reached.

WHY THIS EXISTS (the bug class, stated precisely)
-------------------------------------------------
A G-V12 coverage proof asserts that a mechanism *behaves when called*. Nothing
asserted that it *is called*, or that its output *is read by whatever claims to
read it*. Three mechanisms shipped with passing tests and no caller at all:

  - `ingest_warnings.py`  — documented "auto-updated ... from CI signals" and
    published in the receipts index as "Shipped (v0.16.0)". Invoked by nothing:
    an exhaustive repo-wide search found only its own unit tests and a CI
    path-layout comment that merely *names* the file. Neither `warnings-log.md`
    path had ever existed, in either repo.
  - `validate_mermaid.py` — 87% covered, documented as closing the F11 state-id
    and F13 WCAG-contrast render blind-spots. No render skill invoked it.
  - `verify_citations.py` — tests passed while the matcher matched 0% of real
    citations for ~2.5 months (fixed v0.60.1).

Same shape from the other direction: a reader that resolves a path the writer
never writes. `/xai-check` read `${CLAUDE_PLUGIN_ROOT}/jit-tooling/active-stack.yml`
while the detector spec and both `.gitignore`s named `.claude/jit-tooling/...`,
so `ai_components.detected` was never true and Theory Gate 13 could never fire
(dated to the 2026-05-09 bulk path rewrite, ~2.5 months live).

Three green badges over three disconnected wires. This check is the general
mechanism the 2026-07-25 BVSSH assessment said was missing when it predicted
"a second silently-inert check would still be found by hand."

RULES
-----
A. NO ORPHAN SCRIPTS — every shipped script has a real caller (CI step, hook,
   skill, another script, or the validator), or an allowlist entry stating why
   it has none. A commented-out CI line does NOT count as a caller.
B. PLUGIN-ROOT REFS RESOLVE — every `${CLAUDE_PLUGIN_ROOT}/<path>` in a shipped
   file resolves inside the packaged tree. Repo-root files (AGENTS.md, CLAUDE.md)
   are NOT packaged, so pointing at them through the plugin root is a dead read.
C. ONE PATH PER STATE FILE — for each project-state file in the registry below,
   every reference across the shipped tree agrees on the canonical path. Writer
   and reader disagreeing is invisible from either end alone.
D. AUTOMATION CLAIMS ARE PROMISES — if shipped prose says a named script is
   "auto-updated" / "auto-populated" / "now mechanized" / "Shipped (vX)", that
   script must have a caller. Every bug in this sweep was pre-announced in the
   docs; the claim was checkable evidence nobody had checked. Rule A from the
   documentation side, and the half that still bites when a mechanism has been
   allowlisted out of Rule A.

Usage:
    check_wiring.py [--root REPO_ROOT] [--json]

Exit codes:
    0 — all wiring intact
    1 — at least one break (CI gate)
    2 — argument/setup error

Python stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Rule A — scripts with no caller, and the justified exceptions.
# ---------------------------------------------------------------------------
# Each allowlist entry needs a REASON. "It has a unit test" is not a reason —
# that is precisely the false-green this check exists to catch.
ORPHAN_ALLOWLIST = {
    "safe_replace.py":
        "manual-invocation instrument for agent-authored scripted edits, the "
        "same class as verify_citations.py below. No skill or CI job calls it "
        "because its consumer is the agent mid-task, not a scheduled step. It "
        "is NOT unreachable: agent-operating-contract.md mandates it for any "
        "scripted edit touching more than one file or anchor, and that contract "
        "is injected every session.",
    "_manifest_lib.py":
        "library imported by parse_manifest.py; not independently invoked",
    "check_gated_by.py":
        "documented DRAFT stub, parked pending a 2nd hard violation (see its header)",
    "git-pre-push-example.sh":
        "copy-me template for consumers; invoking it from CI would be wrong",
    "upgrade.sh":
        "legacy (npx-degit) install path, deprecated; invoked by consumers not us",
    "verify_citations.py":
        "manual-invocation instrument BY DESIGN — its own docstring defers "
        "automatic Stop-hook integration until the false-positive rate is "
        "measured. The capture half (hooks/read-log.sh) IS wired; only the "
        "audit half is operator-run. Listed here so that stays a stated "
        "decision rather than an accident, and so docs may not claim it is "
        "automatic (Rule D still polices that).",
}

# Places a script can legitimately be called from.
CALLER_GLOBS = [
    ".github/workflows/*.yml",
    "tests/validate-template.sh",
    "tests/bash/run.sh",
    "plugins/mycelium/hooks/*.sh",
    "plugins/mycelium/skills/*/SKILL.md",
    "plugins/mycelium/scripts/*.py",
    "plugins/mycelium/scripts/*.sh",
    "plugins/mycelium/engine/*.md",
    "plugins/mycelium/orchestration/*.md",
]

# ---------------------------------------------------------------------------
# Rule C — canonical location of every project-state file that more than one
# component touches. Add a row whenever a new state file gains a second reader.
#
# `warnings-log.md` lives under memory/ because that is where the WRITER
# (`ingest_warnings.py`) resolves it and where `/corrections-audit` step 1 reads
# it, alongside its siblings corrections.md and patterns.md. The harness/ form
# was the drift.
# ---------------------------------------------------------------------------
CANONICAL_STATE_PATHS = {
    "warnings-log.md": ".claude/memory/warnings-log.md",
    "active-stack.yml": ".claude/jit-tooling/active-stack.yml",
    "active-metrics.yml": ".claude/jit-tooling/active-metrics.yml",
    "decision-log.md": ".claude/harness/decision-log.md",
    "corrections.md": ".claude/memory/corrections.md",
    "patterns.md": ".claude/memory/patterns.md",
    "cluster-instances.md": ".claude/memory/cluster-instances.md",
}

# Files that legitimately quote a non-canonical path as their SUBJECT rather
# than as a live pointer (migration guides name the old location to delete it).
STATE_PATH_ALLOWLIST = {
    "plugins/mycelium/skills/migrate-from-legacy/SKILL.md",
    "docs/migration.md",
    "docs/changelog.md",
    "docs/install-paths.md",
    "AGENTS.md",
}

# ---------------------------------------------------------------------------
# Rule D — a documentation CLAIM of automation is a promise the wiring must keep.
# ---------------------------------------------------------------------------
# Every bug in the 2026-07-26 sweep was pre-announced in prose and never checked
# against reality. `ingest_warnings.py` was documented "auto-updated ... from CI
# signals" and listed in the receipts index as "Shipped (v0.16.0)" while being
# invoked by nothing. `validate_mermaid.py` was documented as closing two named
# render blind-spots while no skill piped to it. The claim was sitting in plain
# text, in the repo, the whole time — it was evidence nobody had made checkable.
#
# So: when shipped prose says a named script is automatic, that script must have
# a caller. This is Rule A re-entered from the documentation side, and it is the
# half that catches a mechanism whose allowlist entry was added to silence Rule A.
CLAIM_RE = re.compile(
    r"(auto-updated|auto-populated|automatically updated|now mechanized|"
    r"now mechanised|verified mechanically|mechanically verified|"
    r"Shipped \(v[0-9.]+\))",
    re.IGNORECASE,
)
SCRIPT_TOKEN_RE = re.compile(r"\b([a-z0-9_]+\.py)\b")

# Docs whose claim vocabulary is HISTORICAL narration rather than a live promise:
# a changelog recording that something once shipped, or a corrections entry whose
# whole subject is a claim that turned out to be false.
CLAIM_ALLOWLIST = {
    "docs/changelog.md",
    "docs/receipts/cases/2026-05-01-framework-self-correction.md",
}

PLUGIN_REL = "plugins/mycelium"

# This file necessarily quotes the broken paths it exists to catch — its
# docstring names `${CLAUDE_PLUGIN_ROOT}/jit-tooling/active-stack.yml` as the
# worked example. Scanning itself would report its own documentation as a
# defect. Same rationale as check_legacy_paths.py allowlisting the receipts case
# that documents the rot: quoting a bad path as your SUBJECT is not a live
# pointer. Kept to this one file so a real dead ref in a sibling checker is
# still caught.
SELF_EXEMPT = {f"{PLUGIN_REL}/scripts/check_wiring.py"}

# `|` is in the class so brace-alternation is captured whole:
# `domains/{discovery|delivery|quality}/CLAUDE.md` (the operating contract's own
# form) must expand to three candidates. Without it the token truncated at the
# first `|`, silently checking only the first branch — the expansion code below
# was unreachable, which is exactly the never-reached shape this file guards.
REF_PLUGIN_ROOT = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_*./{}|<>-]+)")


def _shipped_files(plugin: Path, root: Path):
    """Every file the plugin actually ships, in a stable order."""
    for f in sorted(plugin.glob("**/*")):
        if not f.is_file() or "__pycache__" in str(f):
            continue
        if str(f.relative_to(root)) in SELF_EXEMPT:
            continue
        if f.suffix in {".md", ".yml", ".json", ".sh", ".py"}:
            yield f


def _expand_braces(tok: str):
    """Expand a single `{a|b|c}` alternation into one candidate per branch."""
    if "{" in tok and "}" in tok:
        pre, rest = tok.split("{", 1)
        inner, post = rest.split("}", 1)
        return [pre + alt + post for alt in inner.split("|")]
    return [tok]


def _is_invocation(line: str, name: str) -> bool:
    """True when `line` actually RUNS `name`, rather than merely naming it.

    THIS DISTINCTION IS THE WHOLE RULE. The first cut of Rule A accepted any
    non-comment line containing the filename, and `engine/*.md` is in the caller
    corpus — so `warning-handbook.md` saying "Consumed by `ingest_warnings.py`"
    counted as wiring, and Rule A would NOT have caught the very bug it was
    written for. A guard with a hole exactly where the bug lives reads green and
    is worse than none; that critique was levelled at check_legacy_paths' dir list
    in this same release, and it applied here too.

    An invocation carries an interpreter or an executable path. A prose mention
    does not. Caught by test_rule_d_claim_about_uncalled_script_is_flagged, which
    failed until this function existed.
    """
    esc = re.escape(name)
    stem = re.escape(Path(name).stem)
    return bool(
        # A LIBRARY MODULE IS REACHED BY IMPORT, not by subprocess. Rule A knew
        # only how to spot an executable being run, so `_text_lib.py` — imported
        # by two guards on the line above — was reported as having no caller at
        # all. Every shared module in the tree was invisible to this rule for the
        # same reason. `import x` and `from . import x` are call sites.
        re.search(r"^\s*(?:from\s+[.\w]*\s+)?import\s+[^\n]*\b" + stem + r"\b", line)
        or re.search(r"^\s*from\s+[.\w]*\b" + stem + r"\b\s+import\b", line)
        or re.search(r"(?:python3?|bash|sh)\b[^\n]*" + esc, line)   # python3 …/x.py
        or re.search(r"(?:^|[\s\"'(=])\./[^\s\"']*" + esc, line)  # ./x.sh
        or re.search(r"\$\{?\w+\}?/[^\s\"']*" + esc, line)        # "$S/x.py"
        # A shell assignment of the script's path is programmatic use: Check 40
        # does `local sync_script="…/sync_derived.py"` and then runs
        # `python3 "$sync_script" --check`, so the interpreter and the filename
        # never share a line. Without this the guard false-positives on every
        # variable-indirected caller.
        or re.search(r"\w+=[\"']?[^\s\"']*" + esc, line),
    )


def _caller_corpus(root: Path):
    """(source, line) for every non-comment line that could invoke a script.

    Comment lines are stripped so a commented-out or merely-mentioning line
    cannot masquerade as wiring — the ingest_warnings failure mode, whose only
    CI reference was a path-layout comment naming the file.
    """
    corpus = []
    for g in CALLER_GLOBS:
        for f in root.glob(g):
            if not f.is_file() or "__pycache__" in str(f):
                continue
            rel = str(f.relative_to(root))
            corpus.extend(
                (rel, line)
                for line in f.read_text(errors="replace").splitlines()
                if not line.lstrip().startswith(("#", "//"))
            )
    return corpus


def check_orphan_scripts(root: Path):
    """Rule A: every shipped script has a caller or a justified allowlist entry."""
    plugin = root / PLUGIN_REL
    scripts_dir = plugin / "scripts"
    if not scripts_dir.is_dir():
        return [], 0

    corpus = _caller_corpus(root)
    findings = []
    examined = 0
    for script in sorted(scripts_dir.iterdir()):
        if not script.is_file() or script.suffix not in {".py", ".sh"}:
            continue
        examined += 1
        name = script.name
        own = f"scripts/{name}"
        if any(not src.endswith(own) and _is_invocation(line, name)
               for src, line in corpus):
            continue
        if name in ORPHAN_ALLOWLIST:
            continue
        findings.append({
            "rule": "A",
            "target": f"{PLUGIN_REL}/scripts/{name}",
            "detail": (
                "shipped script has no caller in CI, hooks, skills, the "
                "validator, or another script (comment lines excluded). Wire "
                "it, or add an ORPHAN_ALLOWLIST entry stating why it has none. "
                "A unit test is not a caller."
            ),
        })
    return findings, examined


def check_plugin_root_refs(root: Path):
    """Rule B: every ${CLAUDE_PLUGIN_ROOT}/<path> resolves in the packaged tree."""
    plugin = root / PLUGIN_REL
    if not plugin.is_dir():
        return [], 0

    findings = []
    examined = 0
    for f in _shipped_files(plugin, root):
        rel = str(f.relative_to(root))
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            for raw in REF_PLUGIN_ROOT.findall(line):
                tok = raw.rstrip(".,;:)`'\"")
                if "*" in tok or "<" in tok:
                    continue
                examined += 1
                findings.extend(
                    {
                        "rule": "B",
                        "target": f"{rel}:{i}",
                        "detail": (
                            f"${{CLAUDE_PLUGIN_ROOT}}/{c} does not exist in the "
                            "packaged tree. Repo-root files are not packaged; "
                            "per-project state belongs under the consumer's "
                            ".claude/, not the shared plugin cache."
                        ),
                    }
                    for c in _expand_braces(tok)
                    if not (plugin / c).exists()
                )
    return findings, examined


def check_state_path_agreement(root: Path):
    """Rule C: every reference to a registered state file uses its canonical path."""
    plugin = root / PLUGIN_REL
    if not plugin.is_dir():
        return [], 0

    findings = []
    examined = 0
    # Match any .claude/<dir>/<basename> occurrence of a registered file.
    patterns = {
        base: re.compile(r"\.claude/[A-Za-z0-9_.-]+/" + re.escape(base))
        for base in CANONICAL_STATE_PATHS
    }
    for f in _shipped_files(plugin, root):
        rel = str(f.relative_to(root))
        if rel in STATE_PATH_ALLOWLIST:
            continue
        for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
            for base, pat in patterns.items():
                canonical = CANONICAL_STATE_PATHS[base]
                examined += len(pat.findall(line))
                findings.extend(
                    {
                        "rule": "C",
                        "target": f"{rel}:{i}",
                        "detail": (
                            f"references `{hit}` but the canonical path for "
                            f"{base} is `{canonical}`. Writer and reader must "
                            "agree — a split path is invisible from either end "
                            "alone."
                        ),
                    }
                    for hit in pat.findall(line)
                    if hit != canonical
                )
    return findings, examined


def check_automation_claims(root: Path):
    """Rule D: a doc claiming a named script is automatic requires that script
    to have a caller.

    Scans shipped docs AND the repo's public docs/ tree, because the strongest
    version of the original false claim lived in `docs/receipts/README.md`
    ("Shipped (v0.16.0)") rather than inside the plugin.
    """
    plugin = root / PLUGIN_REL
    scripts_dir = plugin / "scripts"
    if not scripts_dir.is_dir():
        return [], 0

    shipped_scripts = {p.name for p in scripts_dir.iterdir() if p.suffix == ".py"}
    corpus = _caller_corpus(root)
    called = {
        name
        for name in shipped_scripts
        if any(not src.endswith(f"scripts/{name}") and _is_invocation(line, name)
               for src, line in corpus)
    }

    doc_globs = ["plugins/mycelium/**/*.md", "docs/**/*.md", "README.md"]
    seen = set()
    findings = []
    examined = 0
    for g in doc_globs:
        for f in root.glob(g):
            if not f.is_file() or f in seen:
                continue
            seen.add(f)
            rel = str(f.relative_to(root))
            if rel in CLAIM_ALLOWLIST:
                continue
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                if not CLAIM_RE.search(line):
                    continue
                examined += 1
                findings.extend(
                    {
                        "rule": "D",
                        "target": f"{rel}:{i}",
                        "detail": (
                            f"claims `{tok}` is automatic, but that script has no "
                            "caller in CI, hooks, skills, the validator, or "
                            "another script. Wire it, or correct the claim — a "
                            "promise of automation is the one kind of "
                            "documentation that can be mechanically checked."
                        ),
                    }
                    for tok in dict.fromkeys(SCRIPT_TOKEN_RE.findall(line))
                    if tok in shipped_scripts and tok not in called
                )
    return findings, examined


def scan(root: Path):
    """Return findings AND the size of the population each rule judged.

    The denominators are not decoration. Before v0.74.0 this printed "No wiring
    breaks." with no counts at all, so a run over an empty tree was
    indistinguishable from a run over four hundred files — the check could match
    nothing for months and read green the whole time, which is the exact failure
    `verify_citations` shipped with for three months and the reason CALMS
    Automation sits at amber.
    """
    findings = []
    examined = {}
    for rule, fn in (
        ("A", check_orphan_scripts),
        ("B", check_plugin_root_refs),
        ("C", check_state_path_agreement),
        ("D", check_automation_claims),
    ):
        got, n = fn(root)
        findings += got
        examined[rule] = n
    return {"findings": findings, "examined": examined}


#: A check that CANNOT apply to a repo is a different state from one that
#: applies and found nothing, and v0.74.0/v0.75.0 collapsed the two. Running
#: these in a plugin CONSUMER repo — which has no `plugins/mycelium/` tree at
#: all — produced NOT A PASS on something the user can do nothing about. False
#: alarms are how a check gets ignored, which is the same failure this guard
#: family exists to prevent, arriving from the other side.
#:
#:   precondition ABSENT  -> N/A, exit 0, say which repo kind it is for
#:   precondition PRESENT, population empty -> refuse, exit 1

def main(argv=None):
    p = argparse.ArgumentParser(
        description="Guard against mechanisms that exist but are never reached."
    )
    p.add_argument("--root", default=None, help="Repo root (default: auto-detect).")
    p.add_argument("--json", action="store_true", help="Emit JSON.")
    args = p.parse_args(argv)

    # scripts live at <root>/plugins/mycelium/scripts/
    root = (
        Path(args.root).resolve() if args.root
        else Path(__file__).resolve().parents[3]
    )
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2

    if not (root / PLUGIN_REL).is_dir():
        # N/A, not a failure. See the note above main().
        print(f"Wiring: N/A — no {PLUGIN_REL}/ tree under {root}. This check "
              "guards the FRAMEWORK repo's packaged plugin; a plugin consumer "
              "has nothing for it to reach. Nothing was checked, and nothing "
              "was supposed to be.")
        return 0

    report = scan(root)
    findings = report["findings"]

    # EXIT CODE IS DECIDED BEFORE THE OUTPUT BRANCH (code review 2026-08-03).
    # Every refuse-on-empty branch added in v0.74.0/v0.75.0 lived inside the
    # `else` of `if args.json:`, so the machine-readable path — the one a CI
    # wrapper actually consumes — still exited 0 over an empty population. The
    # release built to remove false green shipped false green on its own JSON
    # surface, and check_empty_input_honesty could not see it because it invokes
    # children with `--root .` only. The verdict is computed once, here, and both
    # renderers report it.
    ex_ = report["examined"]
    if findings:
        rc = 1
    elif not any(ex_.values()):
        rc = 1                      # refused: every rule matched nothing
    else:
        rc = 0

    if args.json:
        print(json.dumps({**report, "verdict": "fail" if rc else "pass"}, indent=2))
        return rc
    ex = report["examined"]
    print(f"Wiring: {ex['A']} shipped script(s) (A), {ex['B']} "
          "${CLAUDE_PLUGIN_ROOT} ref(s) (B), "
          f"{ex['C']} state-path ref(s) (C), {ex['D']} automation claim(s) (D).")
    if findings:
        print(f"\nWIRING BREAKS ({len(findings)}):")
        for f in findings:
            print(f"  [rule {f['rule']}] {f['target']}\n      {f['detail']}")
        print("\nA mechanism nothing reaches is absent, not weak — "
              "and it reads green.")
    elif not any(ex.values()):
        # Refuse the bare pass. Every rule matched an empty population, so
        # "no wiring breaks" is true and carries no information — and a
        # reader takes an unqualified green as coverage.
        print("NOT A PASS: every rule matched an empty population "
              "(0/0/0/0). Nothing was verified. Either --root points "
              "somewhere without a packaged plugin tree, or the patterns "
              "have stopped matching this repo's layout.")
        return 1
    else:
        zeros = [r for r, n in ex.items() if n == 0]
        scope = (f" Rule(s) {'/'.join(zeros)} matched nothing, so this pass "
                 "says nothing about them.") if zeros else ""
        print(f"No wiring breaks across {sum(ex.values())} checked "
              f"reference(s).{scope}")
    return rc

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
