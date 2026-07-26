"""Coverage for check_wiring_contract.py, including proof that it BITES.

The contract is generated from a repo's own majority convention, so the two ways
it can fail are opposite and both must be pinned:

  * **Too lax** — it passes a genuinely orphaned file. The negative controls below
    build a repo with an unreferenced module and require a violation.
  * **Too eager** — it accuses files that are wired by a mechanism it cannot see.
    The false-positive tests pin the two that actually occurred on the first run
    against this repo: fixture trees (synthetic mini-repos built to make guards
    fire, which produced five spurious rules) and discovery-based invocation
    (a runner globbing `tests/bash/test_*.sh` names none of its targets, which
    scored 42-of-50 — just above threshold, so the rule would have shipped and
    then failed on 8 files that were never broken).

A guard whose first act is eight false accusations does not get a second run.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location(
    "check_wiring_contract", _SCRIPTS / "check_wiring_contract.py",
)
cwc = importlib.util.module_from_spec(_spec)
sys.modules["check_wiring_contract"] = cwc
_spec.loader.exec_module(cwc)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


# --------------------------------------------------------------- detection

def test_detects_a_majority_convention_with_its_evidence(tmp_path):
    files = {"run.sh": "#!/bin/bash\n"}
    for i in range(4):
        files[f"scripts/tool{i}.py"] = "def go():\n    return 1\n"
        files["run.sh"] += f"python3 scripts/tool{i}.py\n"
    root = _repo(tmp_path, files)
    got = cwc.detect(root)
    rules = [r for r in got["contracts"] if r["pattern"] == "scripts/*.py"]
    assert rules, got
    assert rules[0]["confidence"] == 1.0
    assert "4 of 4" in rules[0]["detected_from"], "evidence must be recorded, not just a verdict"


def test_a_minority_convention_is_not_proposed(tmp_path):
    """Below threshold it is an aspiration. A contract full of aspirations fails
    on day one and gets deleted."""
    files = {"run.sh": "#!/bin/bash\npython3 scripts/tool0.py\n"}
    for i in range(4):
        files[f"scripts/tool{i}.py"] = "def go():\n    return 1\n"
    root = _repo(tmp_path, files)
    got = cwc.detect(root)
    assert not [r for r in got["contracts"] if r["pattern"] == "scripts/*.py"]


def test_group_below_minimum_size_is_not_a_convention(tmp_path):
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\npython3 scripts/only.py\n",
        "scripts/only.py": "def go():\n    return 1\n",
    })
    assert not [r for r in cwc.detect(root)["contracts"] if "scripts" in r["pattern"]]


def test_fixture_trees_are_not_governed(tmp_path):
    """Fixture trees are synthetic repos built to make a guard fire; the detector
    offered five rules about scaffolding on its first real run."""
    files = {"run.sh": "#!/bin/bash\n"}
    for i in range(4):
        files[f"tests/fixtures/mini/scripts/f{i}.py"] = "x = 1\n"
    root = _repo(tmp_path, files)
    patterns = [r["pattern"] for r in cwc.detect(root)["contracts"]]
    assert not any("fixtures" in p for p in patterns), patterns


def test_glob_invocation_counts_as_a_reference(tmp_path):
    """A runner globbing its targets names none of them."""
    files = {"run.sh": '#!/bin/bash\nfor t in tests/bash/test_*.sh; do bash "$t"; done\n'}
    for i in range(4):
        files[f"tests/bash/test_{i}.sh"] = "#!/bin/bash\necho ok\n"
    root = _repo(tmp_path, files)
    rules = [r for r in cwc.detect(root)["contracts"] if r["pattern"] == "tests/bash/*.sh"]
    assert rules, "glob-invoked files must count as referenced"
    assert rules[0]["confidence"] == 1.0


def test_a_reference_in_a_comment_is_not_a_caller(tmp_path):
    files = {"run.sh": "#!/bin/bash\n# we should call scripts/tool0.py one day\n"}
    for i in range(3):
        files[f"scripts/tool{i}.py"] = "x = 1\n"
    root = _repo(tmp_path, files)
    assert not [r for r in cwc.detect(root)["contracts"] if r["pattern"] == "scripts/*.py"]


# ------------------------------------------------------------- enforcement

def _contract(pattern="scripts/*.py", **extra):
    rule = {"id": "wc-001", "pattern": pattern, "obliges": [{"referenced_by": ["**/*"]}]}
    rule.update(extra)
    return {"contracts": [rule]}


def test_orphan_is_a_violation(tmp_path):
    """THE negative control: a file nothing calls must fail."""
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\npython3 scripts/used.py\n",
        "scripts/used.py": "x = 1\n",
        "scripts/orphan.py": "x = 1\n",
    })
    violations, _ = cwc.enforce(root, _contract())
    assert [v for v in violations if v.path.name == "orphan.py"], violations
    assert not [v for v in violations if v.path.name == "used.py"]


def test_exemption_with_a_reason_suppresses_the_violation(tmp_path):
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\n",
        "scripts/example.py": "x = 1\n",
    })
    c = _contract(exemptions=[{"path": "scripts/example.py", "reason": "copy-me template"}])
    violations, _ = cwc.enforce(root, c)
    assert not violations


def test_ungoverned_files_are_returned_not_hidden(tmp_path):
    """Zero violations across a subset is not zero violations."""
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\npython3 scripts/used.py\n",
        "scripts/used.py": "x = 1\n",
        "src/elsewhere.ts": "export const a = 1;\n",
    })
    violations, ungoverned = cwc.enforce(root, _contract())
    assert not violations
    assert [u for u in ungoverned if u.name == "elsewhere.ts"], ungoverned


def test_sibling_reference_obligation(tmp_path):
    root = _repo(tmp_path, {
        "src/index.ts": "export { Alpha } from './Alpha';\n",
        "src/Alpha.ts": "export const Alpha = 1;\n",
        "src/Beta.ts": "export const Beta = 2;\n",
    })
    c = {"contracts": [{
        "id": "wc-002", "pattern": "src/*.ts",
        "obliges": [{"sibling_reference": "index.ts"}],
    }]}
    violations, _ = cwc.enforce(root, c)
    names = {v.path.name for v in violations}
    assert "Beta.ts" in names
    assert "Alpha.ts" not in names


# --------------------------------------------------------------------- CLI

def _main(root: Path, *extra: str) -> int:
    argv = sys.argv
    sys.argv = ["check_wiring_contract.py", "--root", str(root), *extra]
    try:
        return cwc.main()
    finally:
        sys.argv = argv


def test_missing_contract_is_not_a_pass(tmp_path, capsys):
    """A project with no declared contract has no wiring guarantees. Silence
    here is exactly the absence this guard exists for."""
    _repo(tmp_path, {"scripts/a.py": "x = 1\n"})
    assert _main(tmp_path) == 1
    assert "no contract" in capsys.readouterr().out


def test_bad_root_is_a_usage_error(tmp_path, capsys):
    assert _main(tmp_path / "nope") == 2
    assert "not a directory" in capsys.readouterr().err


def test_detect_mode_emits_reviewable_yaml(tmp_path, capsys):
    files = {"run.sh": "#!/bin/bash\n"}
    for i in range(3):
        files[f"scripts/t{i}.py"] = "x = 1\n"
        files["run.sh"] += f"python3 scripts/t{i}.py\n"
    root = _repo(tmp_path, files)
    assert _main(root, "--detect") == 0
    out = capsys.readouterr().out
    assert "DRAFT wiring contract" in out
    assert "Regenerate rather than hand-edit" in out
    parsed = yaml.safe_load(out)
    assert parsed["contracts"][0]["pattern"] == "scripts/*.py"


def test_violation_exits_1(tmp_path):
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\npython3 scripts/used.py\n",
        "scripts/used.py": "x = 1\n",
        "scripts/orphan.py": "x = 1\n",
        ".claude/harness/wiring-contract.yml": yaml.safe_dump(_contract()),
    })
    assert _main(root) == 1


def test_max_ungoverned_can_gate(tmp_path, capsys):
    root = _repo(tmp_path, {
        "run.sh": "#!/bin/bash\npython3 scripts/used.py\n",
        "scripts/used.py": "x = 1\n",
        "src/a.ts": "export const a = 1;\n",
        "src/b.ts": "export const b = 2;\n",
        ".claude/harness/wiring-contract.yml": yaml.safe_dump(_contract()),
    })
    assert _main(root) == 0, "ungoverned is reported but not gated by default"
    assert _main(root, "--max-ungoverned", "1") == 1
    assert "exceeds" in capsys.readouterr().out


def test_this_repo_satisfies_its_own_contract():
    """Mycelium dogfoods the contract it ships."""
    root = Path(__file__).resolve().parents[2]
    contract_path = root / cwc.CONTRACT_REL
    if not contract_path.is_file():
        pytest.skip("no contract committed yet")
    contract = yaml.safe_load(contract_path.read_text())
    violations, _ = cwc.enforce(root, contract)
    assert not violations, "\n".join(str(v) for v in violations)
