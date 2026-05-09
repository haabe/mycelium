"""Unit tests for parse_manifest.py CLI."""
import subprocess


def test_cli_top_level_returns_files(scripts_path, manifest_path, monkeypatch):
    """parse_manifest.py top_level should print the top_level files space-separated."""
    monkeypatch.chdir(manifest_path.parent.parent)
    r = subprocess.run(
        ["python3", str(scripts_path / "parse_manifest.py"), "top_level"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    files = r.stdout.strip().split()
    assert "CLAUDE.md" in files
    assert "AGENTS.md" in files


def test_cli_directories_returns_paths(scripts_path, manifest_path, monkeypatch):
    monkeypatch.chdir(manifest_path.parent.parent)
    r = subprocess.run(
        ["python3", str(scripts_path / "parse_manifest.py"), "directories"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    assert ".claude/skills/" in r.stdout


def test_cli_unknown_key_exits_1(scripts_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "parse_manifest.py"), "garbage_key"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1
    assert "Unknown key" in r.stderr


def test_cli_no_args_exits_1(scripts_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "parse_manifest.py")],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1
    assert "Usage" in r.stderr


def test_cli_too_many_args_exits_1(scripts_path):
    r = subprocess.run(
        ["python3", str(scripts_path / "parse_manifest.py"), "top_level", "extra"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1


def test_cli_each_valid_key_returns_zero(scripts_path, manifest_path, monkeypatch):
    """All 8 valid keys exit 0 even when their list is empty."""
    monkeypatch.chdir(manifest_path.parent.parent)
    valid_keys = [
        "top_level", "directories", "single_files", "harness_framework",
        "preserved_dir_readmes", "evals_replace", "metrics_adapters_framework",
        "project_state",
    ]
    for key in valid_keys:
        r = subprocess.run(
            ["python3", str(scripts_path / "parse_manifest.py"), key],
            capture_output=True, text=True, check=False,
        )
        assert r.returncode == 0, f"Key '{key}' should exit 0"
