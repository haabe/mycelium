"""check_fail_open must BITE: an unreviewed silent-default site exits 1.

The guard's whole claim is that it can tell "checked, and fine" from "could not
look". A guard that only ever reports and never refuses proves nothing — which
is the rule check_negative_control.py enforces on every shipped guard, and the
reason this file exists rather than a passing-path smoke test.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_fail_open

    return check_fail_open


SILENT = """
def read_thing(p):
    try:
        return open(p).read()
    except OSError:
        return ""
"""

SPEAKS = """
def read_thing(p):
    try:
        return open(p).read()
    except OSError:
        print("WARNING: could not read", p)
        return ""
"""


def test_silent_fail_open_is_flagged_and_strict_exits_1(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    (tmp_path / "mod.py").write_text(SILENT)
    rc = mod.main(["--roots", str(tmp_path), "--reviewed", str(tmp_path / "none.yml"), "--strict"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "SILENT" in out


def test_a_handler_that_speaks_is_reported_as_speaking(scripts_path, tmp_path, capsys):
    """The point is not 'no except clauses'. It is 'the last layer that could speak, spoke'."""
    mod = _import(scripts_path)
    (tmp_path / "mod.py").write_text(SPEAKS)
    mod.main(["--roots", str(tmp_path), "--reviewed", str(tmp_path / "none.yml")])
    assert "appears to speak" in capsys.readouterr().out


def test_unreadable_registry_refuses_rather_than_guessing(scripts_path, tmp_path):
    """An unreadable registry must not make every known site look new."""
    mod = _import(scripts_path)
    bad = tmp_path / "reviewed.yml"
    bad.write_text("reviewed: [oops\n")
    assert mod.main(["--roots", str(tmp_path), "--reviewed", str(bad)]) == 2
