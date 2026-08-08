"""Every shipped check, run against a CONSUMER-shaped repo with planted defects.

WHY THIS EXISTS. `check_empty_input_honesty.py` (v0.79.0) made it impossible for a
shipped check to report success over an EMPTY population, and its own docstring names
the limit it could not close:

    "this catches EMPTY input, not reduced input — a check matching 3 of 300 live
     cases still exits 0 here."

A plugin consumer's repo is not empty. It is the WRONG SHAPE — no `plugins/mycelium/`
tree, no `docs/` in the framework's layout, and all of the project's own content under
`.claude/`. And the wrong shape is the SHIPPED shape: every installation is wrong-shape
relative to the repo the checks were written in.

FOUND 2026-08-08, on a founder question ("seems like the tests or evals ... have lost
their integration and wiring somehow?"). The answer was that nothing had degraded —
two guards had been born upstream-shaped and had never matched a consumer:

  * `check_doc_references` scanned 29 of 212 markdown files in a real dogfood repo and
    reported "no dead references" while 158 links sat unexamined. Three were dead,
    pointing at directories removed by that project's plugin migration 88 days earlier.
  * `check_legacy_paths` — the guard that exists to catch exactly those stale paths —
    reported clean, for the same reason.

WHAT THIS FILE ASSERTS, and the distinction matters. Not "the check runs." Not "the
check exits 0." For each consumer-applicable check: **plant the defect it exists to
catch, in a consumer-shaped tree, and require it to FIND that defect.** A check that
returns PASS over a fixture holding its own defect is the finding.

Checks that genuinely cannot apply to a consumer are listed with the reason and
asserted to say N/A rather than PASS — because "I looked at nothing and everything is
fine" is the one answer that is never true, and it is equally untrue when the reason is
wrong shape rather than emptiness.
"""
import subprocess
import sys

import pytest

#: A consumer repo: project state under .claude/, no plugins/mycelium/ tree, docs
#: outside the framework's layout. Deliberately not a fixture of the upstream repo.
CONSUMER_FILES = {
    "README.md": "# A project using Mycelium\n\nSee [notes](notes.md).\n",
    "notes.md": "# Notes\n",
    ".claude/canvas/README.md": "# Canvas\n\nSee [purpose](purpose.yml).\n",
    ".claude/canvas/purpose.yml": "schema_version: 1\nwhy: because\n",
    ".claude/memory/corrections.md": "# Corrections\n\n### 2026-08-01 — a thing\n\nbody\n",
    ".claude/memory/cluster-instances.md": (
        "| # | Date | Title | Subclass | Outcome |\n|---|---|---|---|---|\n"
        "| 1 | 2026-08-01 | a title | a subclass | an outcome |\n"
    ),
    ".claude/harness/decision-log.md": "# Decisions\n",
}


def _consumer_repo(tmp_path, extra=None):
    """Materialise a consumer-shaped tree, plus any planted defect."""
    for rel, body in {**CONSUMER_FILES, **(extra or {})}.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


def _run(scripts_path, name, root):
    """Run a shipped check against `root`, trying both root-flag spellings."""
    for flag in ("--root", "--project-dir"):
        proc = subprocess.run(
            [sys.executable, str(scripts_path / name), flag, str(root)],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if "unrecognized arguments" not in (proc.stdout + proc.stderr):
            return proc
    return proc


#: (script, planted defect, why this defect is the one it exists to catch)
PLANTED = [
    pytest.param(
        "check_doc_references.py",
        {".claude/canvas/README.md": "# Canvas\n\nSee [schemas](../schemas/canvas/).\n"},
        id="doc_references-finds-dead-link-under-dot-claude",
    ),
    pytest.param(
        "check_legacy_paths.py",
        {".claude/canvas/README.md": "# Canvas\n\nSchemas: `.claude/schemas/canvas/`.\n"},
        id="legacy_paths-finds-moved-dir-ref-under-dot-claude",
    ),
    pytest.param(
        "check_source_class_fidelity.py",
        {".claude/canvas/opportunities.yml": (
            "opportunities:\n"
            "  - id: opp-001\n"
            "    provenance:\n"
            "      evidence_sources:\n"
            '        - "Founder lived experience 2026-08-01"\n'
            "      source_classes:\n"
            "        - external_human\n"
        )},
        id="source_class_fidelity-finds-founder-labelled-external",
    ),
]


@pytest.mark.parametrize(("script", "defect"), PLANTED)
def test_check_finds_its_own_defect_in_a_consumer_tree(
    scripts_path, tmp_path, script, defect
):
    """THE NEGATIVE CONTROL FOR SHAPE. Not 'does it run' — does it FIND."""
    root = _consumer_repo(tmp_path, defect)
    proc = _run(scripts_path, script, root)
    assert proc.returncode == 1, (
        f"{script} returned {proc.returncode} on a consumer-shaped tree holding the "
        f"defect it exists to catch. Output:\n{proc.stdout}\n{proc.stderr}"
    )


@pytest.mark.parametrize(("script", "defect"), PLANTED)
def test_same_check_is_green_on_a_clean_consumer_tree(
    scripts_path, tmp_path, script, defect
):
    """The other half of a negative control: it must not fire on the clean case, or
    the pass above proves nothing about discrimination."""
    root = _consumer_repo(tmp_path)
    proc = _run(scripts_path, script, root)
    assert proc.returncode == 0, (
        f"{script} failed on a CLEAN consumer tree — false positive. Output:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


#: Checks whose subject matter genuinely does not exist in a consumer repo. Each must
#: SAY SO rather than report a pass. The reason is recorded so that a check appearing
#: here wrongly is visible as a claim, not as a silent exemption.
UPSTREAM_ONLY = {
    "check_wiring.py": "audits the framework's own script/workflow wiring",
    "check_negative_control.py": "audits the framework's own guards' tests",
    "check_empty_input_honesty.py": "runs the framework's own checks against an empty tree",
    "check_theory_fidelity.py": "audits docs/theories.md, a framework artifact",
    "check_coverage_floor.py": "reads the framework's coverage.json",
    "check_surface_registry.py": "audits the framework's own surface registry",
}

NA_MARKERS = ("N/A", "not a directory", "coverage json not found", "UNKNOWN")


@pytest.mark.parametrize(("script", "reason"), sorted(UPSTREAM_ONLY.items()))
def test_upstream_only_check_says_na_rather_than_pass(
    scripts_path, tmp_path, script, reason
):
    """An upstream-only check must not report a clean PASS at exit 0 over a consumer
    tree it cannot evaluate. Either it names its precondition, or it exits non-zero."""
    root = _consumer_repo(tmp_path)
    proc = _run(scripts_path, script, root)
    blob = proc.stdout + proc.stderr
    if proc.returncode == 0:
        assert any(m in blob for m in NA_MARKERS), (
            f"{script} exited 0 on a consumer tree without naming its precondition "
            f"({reason}). That reads as a pass over something it never examined.\n{blob}"
        )
