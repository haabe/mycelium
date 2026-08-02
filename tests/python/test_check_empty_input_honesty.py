"""Coverage tests for check_empty_input_honesty.py — the check over the checks (G-V12).

WHY THIS EXISTS. `verify_citations.py` shipped requiring a colon in `(per: X)`.
That form occurs zero times in real output, so for ~3 months it ran on every
push, matched nothing, and reported no problems. Its coverage proof asserted
that it EXECUTES, never that it MATCHES — and no test could have caught it,
because every test fed it the form it wanted.

That set the CALMS Automation green bar on 2026-07-25: *a mechanism that
verifies a shipped check matches live input, not merely that it executes.*
v0.74.0 fixed four such checks by hand, and holding Automation at amber was the
right call precisely because fixing four does not stop the fifth. This is the
fifth-stopper, and these are its own negative controls.

THE DESIGN CHOICE UNDER TEST. The guard RUNS each shipped check against a
genuinely empty repository and reads the exit code. It does not grep sources for
a refusal string, because that would be the same mistake one level up: a
comment, a docstring, or an unreachable branch would satisfy it. Behaviour
cannot be faked by prose about behaviour, and `test_a_docstring_does_not_satisfy
_the_guard` is the assertion that keeps it that way.

Scenario-per-guardpost:
  happy  — a check that refuses on empty        -> pass
  happy  — a check that errors on precondition  -> pass (exit 2 is honest too)
  sad    — a check that exits 0 over nothing    -> FAIL, naming what it printed
  bad    — prose claiming refusal, exit 0       -> FAIL (behaviour, not text)
  bad    — no checks discovered at all          -> FAIL (the guard obeys its own rule)
  edge   — a stub that no longer says it is one -> FAIL (a stale exemption is a hole)
  edge   — real shipped tree                    -> pass (the live gate)
"""
import stat
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_empty_input_honesty

    return check_empty_input_honesty


SCRIPTS_REL = "plugins/mycelium/scripts"


def _fake_check(root, name, body):
    d = root / SCRIPTS_REL
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_text(body)
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return f


HONEST_REFUSAL = """import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--root"); p.parse_args()
print("NOT A PASS: 0 things checked, nothing was verified.")
sys.exit(1)
"""

HONEST_PRECONDITION = """import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--root"); p.parse_args()
print("error: missing docs/theories.md", file=sys.stderr)
sys.exit(2)
"""

VACUOUS_SUCCESS = """import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--root"); p.parse_args()
print("No problems found.")
sys.exit(0)
"""

LIES_IN_PROSE = """import argparse, sys
p = argparse.ArgumentParser(); p.add_argument("--root"); p.parse_args()
# NOT A PASS: this comment claims a refusal the code never performs.
'''On empty input this check refuses and exits 1.'''
print("NOT A PASS: nothing was verified.")
sys.exit(0)          # ...and then exits 0 anyway.
"""


# ------------------------------------------------------------------ happy


def test_a_check_that_refuses_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_honest.py", HONEST_REFUSAL)
    report = mod.scan(tmp_path)
    assert report["findings"] == []
    assert "check_honest.py" in report["checked"]


def test_a_failed_precondition_is_also_honest(scripts_path, tmp_path):
    """Exit 2 is not a pass, so it is not a false pass. Both non-zero forms are fine."""
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_needs_a_file.py", HONEST_PRECONDITION)
    assert mod.scan(tmp_path)["findings"] == []


# ------------------------------------------------------------------ sad


def test_a_check_that_exits_zero_over_nothing_is_flagged(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_vacuous.py", VACUOUS_SUCCESS)
    findings = mod.scan(tmp_path)["findings"]
    assert len(findings) == 1
    assert findings[0]["script"] == "check_vacuous.py"
    assert "No problems found." in findings[0]["detail"], (
        "the finding must quote what the check actually printed, so the reader "
        "sees the false green rather than a description of one"
    )


# ------------------------------------------------------------------ bad


def test_a_docstring_does_not_satisfy_the_guard(scripts_path, tmp_path):
    """THE LOAD-BEARING CASE. A source-grepping implementation would pass this
    file — it contains 'NOT A PASS', a docstring promising a refusal, and even
    prints the refusal line. It then exits 0. Only running it catches that."""
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_liar.py", LIES_IN_PROSE)
    findings = mod.scan(tmp_path)["findings"]
    assert len(findings) == 1
    assert findings[0]["script"] == "check_liar.py"


def test_zero_checks_discovered_is_not_a_pass(scripts_path, tmp_path, capsys):
    """The guard obeys the rule it enforces, or it is the thing it checks for."""
    mod = _import(scripts_path)
    (tmp_path / SCRIPTS_REL).mkdir(parents=True)
    rc = mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "NOT A PASS" in out
    assert "0 shipped checks were discovered" in out


# ------------------------------------------------------------------ edge


def test_a_stale_stub_exemption_is_flagged(scripts_path, tmp_path):
    """An exemption is only valid while its stated reason is still true.

    `check_gated_by.py` is exempt because it declares itself an unimplemented
    stub. If it graduates into a real check and keeps the exemption, the guard
    has a hole exactly where someone stopped looking — so the exemption is
    re-verified against the file every run, not trusted from the table.
    """
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_gated_by.py", VACUOUS_SUCCESS)   # no stub marker
    findings = mod.scan(tmp_path)["findings"]
    assert len(findings) == 1
    assert "no longer says" in findings[0]["detail"]


def test_the_real_tree_passes_its_own_rule(scripts_path, capsys):
    """The live gate, not a fixture. Every shipped check must obey this today."""
    mod = _import(scripts_path)
    root = scripts_path.parents[2]
    rc = mod.main(["--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "refuse to report success over an empty population" in out
    assert "not reduced input" in out, "the pass must state its own scope limit"


def test_absent_precondition_is_not_applicable_not_a_refusal(scripts_path, tmp_path, capsys):
    """A consumer repo ships no checks of its own, so there is nothing to guard."""
    mod = _import(scripts_path)
    (tmp_path / ".claude").mkdir(parents=True)
    rc = mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "N/A" in out
    assert "consumer" in out
    assert "NOT A PASS" not in out


def test_fixture_meets_preconditions_so_checks_are_not_skipped(
    scripts_path, tmp_path
):
    """THE SUBTLE ONE, and the reason the empty fixture is not merely empty.

    The guard runs each shipped check against a throwaway tree. Once N/A exists,
    a bare empty directory makes every check answer "N/A" — so the guard would
    verify NOTHING and report a pass, becoming the exact thing it was built to
    catch. Its fixture therefore CREATES the plugin tree: precondition met,
    population empty. This asserts that a check needing that tree is actually
    exercised rather than skipped into silence.
    """
    mod = _import(scripts_path)
    _fake_check(tmp_path, "check_vacuous.py", VACUOUS_SUCCESS)
    report = mod.scan(tmp_path)
    assert "check_vacuous.py" in [f["script"] for f in report["findings"]], (
        "a vacuous check must still be caught after the N/A change"
    )
