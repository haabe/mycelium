"""Coverage tests for check_leaf_lifecycle.py — the leaf-side half of Check 38.

The defect (dogfood 2026-08-06, opp-036): Check 38 requires non-zero ICE on a
product-leaf CYCLE RECORD; nothing required it on the LEAF. So a leaf could ship
with the selection gate bypassed and nothing noticed, because in a tree whose
opportunities all roll up to the framework no product-leaf cycle could open to
trip Check 38 anyway. Seven shipped leaves in the dogfood canvas carried no ICE.

The placement test matters as much as the logic. This was FIRST written as a
`validate-template.sh` check, which runs in the FRAMEWORK repo — whose canvas has
no shipped leaves. It would have reported "nothing to audit" forever and read
green, which is the built-not-wired class committed inside the fix for a wiring
failure. `test_na_is_not_a_pass` locks in the distinction that caught it.
"""
import json
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_leaf_lifecycle

    return check_leaf_lifecycle


def _canvas(project, body):
    p = project / ".claude" / "canvas" / "opportunities.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_leaf_lifecycle", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


SHIPPED_NO_ICE = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
"""

SHIPPED_WITH_ICE = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_score: {i: 8, c: 6, e: 7, total: 336}
"""


# --- the defect this shipped for -------------------------------------------

def test_shipped_without_ice_fails(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(tmp_path, SHIPPED_NO_ICE)
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "sol-001a" in out
    assert "ice_exempt" in out           # the escape hatch is offered


def test_shipped_with_ice_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _canvas(tmp_path, SHIPPED_WITH_ICE)
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_zero_total_counts_as_unscored(scripts_path, tmp_path):
    """{i:0,c:0,e:0,total:0} is the meta-dogfood shape, not a real score."""
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_score: {i: 0, c: 0, e: 0, total: 0}
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 1


# --- the status variants seen in the real canvas ---------------------------

def test_shipped_variants_are_all_caught(scripts_path, tmp_path, capsys):
    """Substring match on purpose — an exact-match list misses the next variant."""
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-a
        status: partially_shipped
      - id: sol-b
        status: SHIPPED-BEFORE-SCORING
      - id: sol-c
        status: shipped-in-a-different-form
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
    out = capsys.readouterr().out
    for lid in ("sol-a", "sol-b", "sol-c"):
        assert lid in out


def test_unshipped_leaves_are_ignored(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: candidate
      - id: sol-001b
        status: open
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


# --- the escape hatch ------------------------------------------------------

def test_ice_exempt_satisfies_the_check(scripts_path, tmp_path, capsys):
    """A leaf may ship unscored. It may not do so silently."""
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_exempt: "2026-08-06 — emergent from an audit finding, no tradeoff was scored"
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 0
    assert "1 exempted" in capsys.readouterr().out


# --- absent-input discipline, and the placement lesson ---------------------

def test_no_canvas_is_a_precondition_failure_not_a_pass(scripts_path, tmp_path, capsys):
    """Exit 0 here would be a pass over nothing.

    check_empty_input_honesty.py rejected the first version, which SKIPped at
    exit 0. opportunities.yml is a required canvas file: its absence means a
    broken tree, not a project that opted out of having an OST.
    """
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)
    assert _run(mod, "--project-dir", str(tmp_path)) == 2
    assert "NOTHING WAS AUDITED" in capsys.readouterr().err


def test_na_is_not_a_pass(scripts_path, tmp_path, capsys):
    """The distinction that caught the misplacement.

    Written first as a validate-template.sh check, it ran in the framework repo
    whose canvas has no shipped leaves, and would have read green forever. "Nothing
    shipped yet" and "everything shipped is scored" must not print the same thing.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: candidate
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "no-shipped-leaves" in out
    assert "not a pass over a population" in out
    assert "OK" not in out


def test_malformed_canvas_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(tmp_path, "opportunities: [unclosed\n")
    assert _run(mod, "--project-dir", str(tmp_path)) == 2
    assert "ERROR" in capsys.readouterr().err


def test_opportunities_not_a_list_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(tmp_path, "opportunities: not-a-list\n")
    assert _run(mod, "--project-dir", str(tmp_path)) == 2
    assert "not a list" in capsys.readouterr().err


def test_bad_project_dir_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    assert _run(mod, "--project-dir", str(tmp_path / "nope")) == 2
    assert "not a directory" in capsys.readouterr().err


def test_json_output(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _canvas(tmp_path, SHIPPED_NO_ICE)
    assert _run(mod, "--project-dir", str(tmp_path), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "violations"
    assert payload["violations"][0]["id"] == "sol-001a"
    assert payload["shipped_leaves"] == 1
