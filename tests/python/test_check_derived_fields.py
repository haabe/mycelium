"""Coverage for check_derived_fields: a pointer resolves, a cache beside it is compared."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_derived_fields.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cdf", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cdf"] = m
    spec.loader.exec_module(m)
    return m


def _project(tmp_path):
    p = tmp_path / "proj"
    (p / ".claude" / "canvas").mkdir(parents=True)
    (p / ".claude" / "diamonds").mkdir()
    (p / ".claude" / "evals" / "metrics" / "github").mkdir(parents=True)
    (p / ".claude" / "evals" / "metrics" / "github" / "2026-09-03.json").write_text(
        json.dumps({"primary_counts": {"stars": 42}}))
    (p / ".claude" / "evals" / "metrics" / "github" / "2026-09-10.json").write_text(
        json.dumps({"primary_counts": {"stars": 45}}))
    (p / ".claude" / "canvas" / "cycle-history.yml").write_text(
        "cycles:\n  - {cycle_id: c1, terminal_state: killed}\n  - {cycle_id: c2, terminal_state: launched}\n")
    (p / ".claude" / "canvas" / "north-star.yml").write_text(
        "input_metrics:\n"
        "  - id: adoption\n    current_value:\n"
        "      stars_total: {source_ref: 'metrics/github#primary_counts.stars', value: 42}\n"
        "  - id: waste\n    current_value:\n"
        "      cycles_total: {source_ref: 'cycle-history.yml#cycles|count'}\n"
        "      killed: {source_ref: 'cycle-history.yml#cycles|count terminal_state=killed', value: 1}\n"
        "      by_id: {source_ref: 'cycle-history.yml#cycles.c2.terminal_state'}\n"
        "      bad: {source_ref: 'cycle-history.yml#nothing.here'}\n"
        "      nosnap: {source_ref: 'metrics/linkedin#x'}\n")
    return p


def test_pointers_resolve_count_and_compare_caches(tmp_path):
    m = _mod()
    p = _project(tmp_path)
    assert m.resolve("metrics/github#primary_counts.stars", p) == (45, "")
    assert m.resolve("cycle-history.yml#cycles|count", p) == (2, "")
    assert m.resolve("cycle-history.yml#cycles|count terminal_state=killed", p) == (1, "")
    assert m.resolve("cycle-history.yml#cycles.c2.terminal_state", p) == ("launched", "")
    assert m.resolve("cycle-history.yml#cycles.1.terminal_state", p) == ("launched", "")
    assert m.resolve("cycle-history.yml#nothing.here", p)[1] == "no key or id `nothing`"
    assert "no snapshots" in m.resolve("metrics/linkedin#x", p)[1]
    assert m.resolve("garbage", p)[1] == "malformed pointer"
    assert m.resolve("cycle-history.yml#cycles.c1.terminal_state|count", p)[1] == "count on a non-list"
    assert "no file" in m.resolve("missing.yml#a", p)[1]
    assert len(m.pointers(p)) == 6


def test_report_names_diverged_and_unresolved(tmp_path, capsys, monkeypatch):
    m = _mod()
    p = _project(tmp_path)
    monkeypatch.setattr("sys.argv", ["x", "--project-dir", str(p)])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "DIVERGED   [canvas/north-star.yml] input_metrics[adoption].current_value.stars_total: cache 42, source says 45" in out
    assert "6 pointer(s): 3 resolved, 1 DIVERGED, 2 unresolved" in out
    assert "UNRESOLVED [canvas/north-star.yml] input_metrics[waste].current_value.bad" in out


def test_nothing_to_resolve_is_not_a_pass_and_missing_canvas_is_a_precondition(tmp_path):
    p = tmp_path / "bare"
    (p / ".claude" / "canvas").mkdir(parents=True)
    (p / ".claude" / "canvas" / "x.yml").write_text("a: 1\n")
    r = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(p)],
                       capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "NOT A PASS" in r.stdout
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(tmp_path / "none")],
                        capture_output=True, text=True, check=False)
    assert r2.returncode == 2


# ---------------------------------------------------------------- mutation survivors (2026-10-11)
# Lines no test constrained: only `id` and `*_id` keys name an item; an index equal to the list's
# length is not an index; a count that matches more than one item; an item with no id is labelled
# by its position; and the depth limit, through dicts and through lists.

def test_only_an_id_key_names_an_item():
    m = _mod()
    assert m._is({"id": "a", "name": "b"}, "a") and m._is({"cycle_id": "c"}, "c")
    assert not m._is({"id": "a", "name": "b"}, "b")


def test_an_index_equal_to_the_length_is_read_as_an_id(tmp_path):
    m = _mod()
    p = _project(tmp_path)
    assert m.resolve("cycle-history.yml#cycles.2.terminal_state", p) == (None, "no item id `2`")


def test_a_count_with_a_condition_counts_every_match(tmp_path):
    m = _mod()
    p = _project(tmp_path)
    (p / ".claude" / "canvas" / "cycle-history.yml").write_text(
        "cycles:\n  - {cycle_id: c1, terminal_state: killed}\n"
        "  - {cycle_id: c2, terminal_state: killed}\n  - {cycle_id: c3, terminal_state: launched}\n")
    assert m.resolve("cycle-history.yml#cycles|count terminal_state=killed", p) == (2, "")


def test_an_item_with_no_id_is_labelled_by_its_position():
    m = _mod()
    assert m._item_label({"name": "n"}, 3) == "3"
    assert m._item_label("a scalar", 1) == "1"
    assert m._item_label({"id": "x"}, 0) == "x"


def test_a_pointer_at_the_depth_limit_is_collected_and_one_below_it_is_not():
    m = _mod()
    for as_list in (False, True):
        for depth, seen in ((m._MAX_DEPTH, 1), (m._MAX_DEPTH + 1, 0)):
            node = {"source_ref": "x.yml#a", "value": 1}
            for _ in range(depth):
                node = [node] if as_list else {"k": node}
            out: list = []
            m._collect(node, "c", "", out)
            assert len(out) == seen, (as_list, depth)
