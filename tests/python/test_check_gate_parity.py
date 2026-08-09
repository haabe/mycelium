"""Coverage proof for check_gate_parity.py, and proof that it bites.

The guard exists because a gate list lived in two hand-maintained files and
drifted to 11-against-4. A test that only asserted the happy path would be the
same class of defect one level up: a check that has never been red has not been
tested, it has been run. Every test below that matters plants the defect and
requires it to be FOUND.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "mycelium" / "scripts" / "check_gate_parity.py"

sys.path.insert(0, str(SCRIPT.parent))
import check_gate_parity as cgp  # noqa: E402

WORKFLOW = """\
name: validate
jobs:
  build:
    steps:
      - name: Run wiring guard
        run: python3 plugins/mycelium/scripts/check_wiring.py --root .
      - name: Run negative-control guard
        run: python3 plugins/mycelium/scripts/check_negative_control.py --root .
"""

GATE_SET = """\
# comment line
check_wiring.py --root .
check_negative_control.py --root .
"""


def _tree(tmp_path: Path, workflow: str, gate_set: str) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "validate.yml").write_text(workflow)
    scripts = tmp_path / "plugins" / "mycelium" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "local-gate-set.txt").write_text(gate_set)
    return tmp_path


def test_parity_holds_when_both_lists_agree(tmp_path):
    root = _tree(tmp_path, WORKFLOW, GATE_SET)
    result = cgp.evaluate(root)
    assert result["status"] == "ok"
    assert result["ci_count"] == 2
    assert result["missing"] == []


def test_a_ci_only_gate_is_found(tmp_path):
    """THE DEFECT THIS GUARD EXISTS FOR. Plant it; require detection."""
    root = _tree(tmp_path, WORKFLOW, "check_wiring.py --root .\n")
    result = cgp.evaluate(root)
    assert result["status"] == "fail"
    assert result["missing"] == ["check_negative_control.py"]


def test_seven_ci_only_gates_are_all_reported_not_just_the_first(tmp_path):
    """The real 2026-08-09 shape was seven at once, not one."""
    seven = [f"check_thing_{i}.py" for i in range(7)]
    workflow = "steps:\n" + "".join(
        f"      - run: python3 plugins/mycelium/scripts/{s} --root .\n" for s in seven
    )
    root = _tree(tmp_path, workflow, "# none declared\n")
    result = cgp.evaluate(root)
    assert result["status"] == "fail"
    assert result["missing"] == seven


def test_a_waiver_with_a_reason_satisfies_parity(tmp_path):
    root = _tree(
        tmp_path,
        WORKFLOW,
        "check_wiring.py --root .\n!waived check_negative_control.py needs a network fixture\n",
    )
    result = cgp.evaluate(root)
    assert result["status"] == "ok"
    assert result["waived"] == {"check_negative_control.py": "needs a network fixture"}


def test_a_waiver_without_a_reason_does_not_count_as_a_waiver(tmp_path):
    """A bare `!waived x` must not silence the gate.

    Otherwise the cheapest way past this check is a line that explains nothing,
    which is how a waiver mechanism becomes an off switch.
    """
    root = _tree(
        tmp_path, WORKFLOW, "check_wiring.py --root .\n!waived check_negative_control.py\n"
    )
    result = cgp.evaluate(root)
    assert result["status"] == "fail"
    assert result["missing"] == ["check_negative_control.py"]


def test_a_gate_named_only_in_a_comment_is_not_counted(tmp_path):
    """The false positive that would have fired on the real workflow.

    `validate.yml` mentions `check_source_independence.py` inside a comment
    explaining what a field feeds; that script is invoked by the canvas-health
    skill, not by CI. Counting the comment manufactures a missing-gate finding
    about a correctly-wired check — a false positive on first contact with real
    data, which is how a guard earns an exclusion list instead of trust.
    """
    workflow = WORKFLOW + (
        "      # machine-consumed: check_source_independence.py counts things\n"
        "      # run: python3 plugins/mycelium/scripts/check_disabled_step.py --root .\n"
    )
    root = _tree(tmp_path, workflow, GATE_SET)
    result = cgp.evaluate(root)
    assert result["status"] == "ok", result
    assert "check_source_independence.py" not in result["missing"]
    assert "check_disabled_step.py" not in result["missing"]


def test_consumer_tree_is_a_precondition_failure_not_a_pass(tmp_path):
    """Absence must not be laundered into a pass (anti-pattern #9).

    The first version returned 0 here and `check_empty_input_honesty.py` rejected
    it on the first local gate-set run. Exit 2 matches check_theory_fidelity.
    """
    result = cgp.evaluate(tmp_path)
    assert result["status"] == "precondition"
    assert "Nothing was compared" in result["detail"]
    assert cgp.main(["--root", str(tmp_path)]) == 2


def test_a_workflow_that_invokes_nothing_refuses(tmp_path):
    """Input present, nothing verified — refuse (1), do not pass."""
    root = _tree(tmp_path, "name: validate\njobs: {}\n", GATE_SET)
    result = cgp.evaluate(root)
    assert result["status"] == "refuse"
    assert "verified nothing" in result["detail"]
    assert cgp.main(["--root", str(root)]) == 1


def test_cli_exit_codes(tmp_path):
    ok = _tree(tmp_path / "ok", WORKFLOW, GATE_SET)
    bad = _tree(tmp_path / "bad", WORKFLOW, "check_wiring.py --root .\n")
    assert cgp.main(["--root", str(ok)]) == 0
    assert cgp.main(["--root", str(bad)]) == 1
    assert cgp.main(["--root", str(tmp_path / "absent")]) == 2


def test_runs_as_a_script_against_the_real_repo(tmp_path):
    """Reaches the shipped file the way CI and the hook do."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(REPO)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Gate parity: OK" in proc.stdout


# --- The live contract: the real repo's own two lists must agree -------------


def test_the_real_repos_lists_agree_right_now():
    """Not a duplicate of the CLI test: this one names the numbers.

    If someone adds a CI step and forgets the gate set, this fails in the same
    pytest run that the pre-push hook already invokes.
    """
    result = cgp.evaluate(REPO)
    assert result["status"] == "ok", result.get("missing")
    assert result["ci_count"] >= 11, "CI lost gates — check validate.yml"


def test_the_gate_set_only_names_scripts_that_exist():
    """A set naming a deleted script would fail the hook for the wrong reason."""
    scripts_dir = REPO / "plugins" / "mycelium" / "scripts"
    text = (scripts_dir / "local-gate-set.txt").read_text()
    declared, _ = cgp.parse_gate_set(text)
    missing = [g for g in declared if not (scripts_dir / g).is_file()]
    assert not missing, f"gate set names non-existent script(s): {missing}"


@pytest.mark.parametrize("gate", ["check_gate_parity.py", "check_coverage_floor.py"])
def test_the_set_contains_its_own_guard_and_the_coverage_floor(gate):
    """The parity guard must gate itself, or CI can outrun it silently."""
    text = (REPO / "plugins" / "mycelium" / "scripts" / "local-gate-set.txt").read_text()
    declared, _ = cgp.parse_gate_set(text)
    assert gate in declared
