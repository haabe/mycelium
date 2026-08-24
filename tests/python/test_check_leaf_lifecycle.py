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

# CARRIES four_risks SINCE 2026-08-24, and the reason is recorded rather than silent:
# this fixture means "a properly recorded shipped leaf", and after the four-risks half
# shipped, a leaf with ICE and no risk block is a violation by the founder's ruling. The
# tests below still isolate the ICE dimension — the risk block is here so they are not
# accidentally asserting the ABSENCE of the new check.
SHIPPED_WITH_ICE = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_score: {i: 8, c: 6, e: 7, total: 336}
        four_risks: {value: v, usability: u, feasibility: f, viability: vi}
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
    """A leaf may ship unscored. It may not do so silently.

    Carries `four_risks` since 2026-08-24 so this isolates the ICE escape hatch rather
    than tripping the four-risks half — see the note on SHIPPED_WITH_ICE.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_exempt: "2026-08-06 — emergent from an audit finding, no tradeoff was scored"
        four_risks: {value: v, usability: u, feasibility: f, viability: vi}
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
    assert "no-decision-point-leaves" in out
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


# --- the four-risks half (2026-08-24) --------------------------------------
# The 2026-08-23 census counted 19 of 54 leaves carrying `four_risks` and read it as a
# sprawling backlog. Recounted by status it is three different things: 24 still
# `candidate` (pre-decision, rule says SHOULD, a filled block there is the filler trap),
# 4 closed (nothing to assess), and 7 that passed a decision with no risk evaluation.
# These tests pin the split, because counting the population is what hid the 7.

FR_VALIDATED_NO_RISKS = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: validated
        ice_score: {i: 8, c: 6, e: 7, total: 336}
"""

FR_CANDIDATE_NO_RISKS = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: candidate
"""

FR_DISCARDED_NO_RISKS = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: discarded
"""

FR_SHIPPED_WITH_RISKS = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_score: {i: 8, c: 6, e: 7, total: 336}
        four_risks:
          value: "founder-requested directly"
          usability: "a prompt interrupts at a moment nobody chose"
          feasibility: "one CI step and one gate-set line"
          viability: "framework surface"
"""

FR_SHIPPED_EMPTY_RISKS = """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: shipped
        ice_score: {i: 8, c: 6, e: 7, total: 336}
        four_risks:
          value: ""
          usability: ""
"""


def test_validated_without_four_risks_fails(scripts_path, tmp_path, capsys):
    """`validated` is a decision point even though it never shipped. Founder ruling."""
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_VALIDATED_NO_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path)) == 1
    out = capsys.readouterr().out
    assert "four_risks" in out and "sol-001a" in out


def test_candidate_without_four_risks_is_not_flagged(scripts_path, tmp_path):
    """The 24 the census counted. Pre-decision; the rule says SHOULD, not MUST."""
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_CANDIDATE_NO_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_discarded_without_four_risks_is_not_flagged(scripts_path, tmp_path):
    """Nothing was invested, so there is nothing a risk assessment would have protected."""
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_DISCARDED_NO_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_shipped_with_four_risks_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_SHIPPED_WITH_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_empty_four_risks_block_is_unassessed(scripts_path, tmp_path):
    """A key with nothing under it is the filler trap, not a pass.

    If this ever returns 0 the check certifies the exact shape it was written to find.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_SHIPPED_EMPTY_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path)) == 1


def test_four_risks_exempt_with_a_reason_satisfies(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_VALIDATED_NO_RISKS.replace(
        "status: validated",
        "status: validated\n        four_risks_exempt: 'emergent fix, no selection decision'"))
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_ice_half_is_not_widened_to_validated(scripts_path, tmp_path):
    """The two halves use different populations ON PURPOSE.

    ICE keys on SHIPPED because it is the Check 38 precondition. Four-risks keys on
    shipped OR validated because the rule is about passing a decision. Widening the ICE
    half under cover of adding the new one would change a shipped mechanism's behaviour.
    This validated leaf has no ICE and must NOT be reported as an ICE violation.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, """
opportunities:
  - id: opp-001
    solutions:
      - id: sol-001a
        status: validated
        four_risks: {value: "v", usability: "u", feasibility: "f", viability: "vi"}
""")
    assert _run(mod, "--project-dir", str(tmp_path)) == 0


def test_json_keeps_the_ice_key_meaning_ice(scripts_path, tmp_path, capsys):
    """session-start.sh reads `violations` and prints an ICE sentence from its length.

    Repurposing that key would make a four-risks-only finding render as
    "0 shipped leaves carry no ICE". This locks the contract.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, FR_VALIDATED_NO_RISKS)
    assert _run(mod, "--project-dir", str(tmp_path), "--json") == 1
    d = json.loads(capsys.readouterr().out)
    assert d["status"] == "violations"
    assert d["violations"] == []                      # ICE half clean
    assert len(d["four_risks_violations"]) == 1       # the new half
    assert all(k in d for k in ("shipped_leaves", "exempted"))  # backward compat
