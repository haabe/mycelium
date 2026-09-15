"""Coverage for check_primary_theory_gated: the join between primary theories and gates."""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins/mycelium/scripts/check_primary_theory_gated.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cptg", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cptg"] = m
    spec.loader.exec_module(m)
    return m


def _engine(tmp_path, table, scales):
    root = tmp_path / "fw"
    (root / "engine").mkdir(parents=True)
    (root / "engine" / "diamond-rules.md").write_text(table)
    import yaml
    (root / "engine" / "confidence-thresholds.yml").write_text(yaml.safe_dump({"scales": scales}))
    return root


TABLE = ("| Scale | Name | Focus | Primary Theories | Duration | Example |\n"
         "|---|---|---|---|---|---|\n"
         "| **L1** | Strategy | Where | Wardley Mapping, North Star, Team Topologies (Skelton) | w | e |\n"
         "| **L2** | Opportunity | What | Torres (CDH/OST), Cynefin (Snowden), Made-up (Nobody) | d | e |\n")


def test_join_classifies_gated_ungated_and_unmapped(tmp_path):
    m = _mod()
    primary = m.parse_primary_theories(_engine(tmp_path, TABLE, {}) / "engine" / "diamond-rules.md")
    assert primary["L1"] == ["Wardley Mapping", "North Star", "Team Topologies (Skelton)"]
    res = m.join(primary, {"L1": {"required_theory_gates": ["evidence", "landscape"]},
                           "L2": {"required_theory_gates": ["evidence", "cynefin"]}})
    assert ("L1", "Wardley Mapping") in res["gated"]
    assert ("L1", "Team Topologies (Skelton)") in res["ungated"]
    assert ("L1", "North Star") in res["ungated"]           # mapped to None: no gate anywhere
    assert ("L2", "Made-up (Nobody)") in res["unmapped"]     # not guessed
    assert ("L2", "Torres (CDH/OST)") in res["gated"]


def test_the_shipped_engine_joins_and_names_l1s_new_gates():
    """The real tree: after 0.217.0, Wardley and Skelton are gated at L1."""
    m = _mod()
    root = REPO / "plugins/mycelium"
    primary = m.parse_primary_theories(root / "engine" / "diamond-rules.md")
    import yaml
    scales = yaml.safe_load((root / "engine" / "confidence-thresholds.yml").read_text())["scales"]
    res = m.join(primary, scales)
    assert ("L1", "Wardley Mapping") in res["gated"]
    assert ("L1", "Team Topologies (Skelton)") in res["gated"]
    assert not res["unmapped"], res["unmapped"]


def test_cli_reports_and_refuses_over_nothing(tmp_path, capsys, monkeypatch):
    m = _mod()
    root = _engine(tmp_path, TABLE, {"L1": {"required_theory_gates": ["landscape"]}})
    monkeypatch.setattr("sys.argv", ["x", "--framework-root", str(root)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "UNGATED   L1: Team Topologies (Skelton)" in out and "unmapped  L2: Made-up" in out
    empty = _engine(tmp_path / "e", "no table\n", {})
    monkeypatch.setattr("sys.argv", ["x", "--framework-root", str(empty)])
    assert m.main() == 1
    monkeypatch.setattr("sys.argv", ["x", "--framework-root", str(tmp_path / "nowhere")])
    assert m.main() == 2
    r = subprocess.run([sys.executable, str(SCRIPT), "--framework-root", str(root)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0 and "primary-theory/scale pairs" in r.stdout
