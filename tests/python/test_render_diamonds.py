"""render_diamonds.py (v0.309.0, stage 5d-3, DL-1372 V4): a diamond is drawn as the decisions it
recorded, in order, grouped by the mode it was in, then what is still to come.

Until this release /diamond-render was a spec the agent drew by hand, in four phases, and it listed
seven fixtures that did not exist. These tests are the first that run against what it draws."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import render_diamonds as rd  # noqa: E402
import scale_locks as sl  # noqa: E402
import validate_mermaid as vm  # noqa: E402


def _dec(name, on):
    return {"decision": name, "on": on}


L0 = {"id": "l0-p", "scale": "L0", "name": "Purpose", "confidence": 0.6,
      "decisions": [_dec("state_purpose", "2026-09-01")]}
L1 = {"id": "l1-s", "scale": "L1", "name": "Strategy", "parent": "l0-p", "created_at": "2026-09-02",
      "decisions": [_dec("set_target", "2026-09-02")]}
# DL-1373: the first test read inconclusive, so a second experiment is APPENDED after the build.
L3 = {"id": "l3-t", "scale": "L3", "name": "Test", "parent": "l1-s", "confidence": 0.4,
      "decisions": [_dec("set_target", "2026-09-03"), _dec("start_experiment", "2026-09-04"),
                    _dec("commit_to_build", "2026-09-04"), _dec("start_experiment", "2026-09-10")]}
DONE = {"id": "l3-done", "scale": "L3", "name": "Done",
        "decisions": [_dec("set_target", "2026-08-01"), _dec("start_experiment", "2026-08-02"),
                      _dec("commit_to_build", "2026-08-02"), _dec("release", "2026-08-05"),
                      _dec("close", "2026-08-20")]}


def _project(tmp_path, active=(L0, L1, L3), completed=(DONE,)):
    d = tmp_path / ".claude" / "diamonds"
    d.mkdir(parents=True)
    (d / "active.yml").write_text(yaml.safe_dump(
        {"active_diamonds": list(active), "completed_diamonds": list(completed)}, sort_keys=False))
    return tmp_path


def _run(capsys, *args):
    rc = rd.main(list(args))
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_a_repeated_decision_is_drawn_where_it_happened(tmp_path, capsys):
    """DL-1373: a loop iterates by appending. The second `start_experiment` is a step of its own,
    after the build, in delivery mode, and the position does not move back."""
    root = _project(tmp_path)
    rc, out, _ = _run(capsys, "--project-dir", str(root), "--format", "json", "--scale", "L3")
    assert rc == 0
    v = next(x for x in json.loads(out)["diamonds"] if x["id"] == "l3-t")
    assert [(r["decision"], r["mode"]) for r in v["recorded"]] == [
        ("set_target", "discovery"), ("start_experiment", "discovery"),
        ("commit_to_build", "delivery"), ("start_experiment", "delivery")]
    assert v["position"] == sl.position(L3) == "committed to build (delivery)"
    assert [u["decision"] for u in v["upcoming"]] == ["release", "close"]


def test_a_close_is_drawn_in_the_mode_it_is_taken_in(tmp_path, capsys):
    root = _project(tmp_path)
    rc, out, _ = _run(capsys, "--project-dir", str(root), "--format", "json", "--scale", "all")
    views = {v["id"]: v for v in json.loads(out)["diamonds"]}
    assert views["l3-t"]["upcoming"][-1] == {**views["l3-t"]["upcoming"][-1], "mode": "delivery"}
    done = views["l3-done"]
    assert done["recorded"][-1]["mode"] == "delivery" and done["mode"] == "closed"
    assert done["upcoming"] == []


def test_an_l0_states_its_purpose_and_reviews_it(tmp_path, capsys):
    root = _project(tmp_path)
    rc, out, _ = _run(capsys, "--project-dir", str(root), "--format", "ascii", "--scale", "L0")
    assert rc == 0
    assert "L0 Purpose: purpose stated" in out
    assert "* state_purpose 2026-09-01" in out and ". review (when the purpose drifts)" in out
    assert "set_target" not in out, "an L0 is not a loop (DL-1368 S2)"


def test_active_draws_the_open_diamonds_and_all_draws_every_one(tmp_path, capsys):
    root = _project(tmp_path)
    _, out, _ = _run(capsys, "--project-dir", str(root), "--format", "json")
    assert [v["id"] for v in json.loads(out)["diamonds"]] == ["l0-p", "l1-s", "l3-t"]
    _, out, _ = _run(capsys, "--project-dir", str(root), "--format", "json", "--scale", "all")
    assert [v["id"] for v in json.loads(out)["diamonds"]] == ["l0-p", "l1-s", "l3-t", "l3-done"]


def _scopes_of_class_targets(diagram: str) -> list[tuple[str, str, str]]:
    """(target, block where the target is declared, block where its class line is), by indent."""
    stack, declared_in, out = ["<root>"], {}, []
    for line in diagram.splitlines():
        m = re.match(r'^\s*state ".*" as (\w+) \{$', line)
        if m:
            stack.append(m.group(1))
            continue
        if line.strip() == "}":
            stack.pop()
            continue
        m = re.match(r"^\s*(\w+) : ", line)
        if m and "-->" not in line:
            declared_in[m.group(1)] = stack[-1]
        m = re.match(r"^\s*class (\w+) \w+$", line)
        if m:
            out.append((m.group(1), declared_in.get(m.group(1), "?"), stack[-1]))
    return out


def test_the_mermaid_is_valid_and_each_state_stays_in_its_mode(tmp_path, capsys):
    """The first render put each `class` line in the diamond's scope, outside the mode block that
    declares the state: Mermaid then drew every decision outside its mode. A class line must sit
    in the block that declares its state."""
    root = _project(tmp_path)
    rc, out, _ = _run(capsys, "--project-dir", str(root))
    assert rc == 0
    fails, refs = vm.check_state_ids(out)
    assert not fails and refs > 0, fails
    fails, passes = vm.check_contrast(out)
    assert not fails and passes, fails
    placed = _scopes_of_class_targets(out)
    assert placed, "a current decision is marked"
    assert all(decl == where for _, decl, where in placed), placed
    assert "D1 --> D2 : opened 2026-09-02" in out, "the child is linked to its parent"

    # Control: the first render's shape, a class line one block out, is caught.
    bad = ('  state "x" as D1 {\n    state "discovery" as D1_m1 {\n      D1_1 : set_target\n'
           '    }\n    class D1_1 current\n  }\n')
    assert [(t, decl, where) for t, decl, where in _scopes_of_class_targets(bad)] == [
        ("D1_1", "D1_m1", "D1")]


def test_formats_and_scales_it_does_not_draw_fail_loud(tmp_path, capsys):
    root = _project(tmp_path)
    rc, _, err = _run(capsys, "--project-dir", str(root), "--format", "markdown-table")
    assert rc == 2 and "FORMAT NOT SUPPORTED" in err
    rc, _, err = _run(capsys, "--project-dir", str(root), "--scale", "L4")
    assert rc == 2 and "NO L4 DIAMOND" in err
    rc, _, err = _run(capsys, "--project-dir", str(root), "--scale", "L9")
    assert rc == 2 and "UNKNOWN SCALE" in err


def test_no_open_diamond_says_so_and_passes(tmp_path, capsys):
    root = _project(tmp_path, active=(), completed=())
    rc, out, _ = _run(capsys, "--project-dir", str(root))
    assert rc == 0 and out.strip() == rd.NO_DIAMOND
