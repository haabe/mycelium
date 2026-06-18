"""Coverage tests for check_gated_by.py — the DRAFT/NOT-WIRED stub.

The script is a parking-state stub: main() prints the design notes to stderr
and returns 0 unconditionally. These lock the documented contract (exit 0,
message on stderr) so a future graduation that changes behaviour is a
deliberate, visible diff.
"""
import subprocess
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_gated_by  # noqa: PLC0415

    return check_gated_by


def test_main_returns_zero(scripts_path):
    mod = _import(scripts_path)
    assert mod.main() == 0


def test_main_writes_draft_notice_to_stderr(scripts_path, capsys):
    mod = _import(scripts_path)
    mod.main()
    captured = capsys.readouterr()
    assert "DRAFT stub" in captured.err
    assert captured.out == ""


def test_cli_invocation_exit_zero(scripts_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "check_gated_by.py")],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    assert "Graduation criterion" in r.stderr
