"""Coverage tests for integrations/opencode/check-tool-calling.py.

The filename has a hyphen, so it cannot be imported by module name. We load it
by file path with importlib.util.spec_from_file_location and stub its network
call (`post`) so no live Ollama is required.

Branches covered:
  - structured tool_calls present -> PASS, return 0
  - tool_calls absent (leaked to text) -> FAIL, return 1
  - network/Ollama error -> ERROR, return 2
  - default model + OLLAMA_HOST handling at module load
"""
import importlib.util
from pathlib import Path

import pytest


def _module_path():
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent
    return repo_root / "plugins" / "mycelium" / "integrations" / "opencode" / "check-tool-calling.py"


def _load(monkeypatch=None, argv=None, env=None):
    """Load check-tool-calling.py by file path (hyphenated -> not importable by name)."""
    path = _module_path()
    if monkeypatch is not None:
        if argv is not None:
            monkeypatch.setattr("sys.argv", argv)
        for k, v in (env or {}).items():
            monkeypatch.setenv(k, v)
    spec = importlib.util.spec_from_file_location("check_tool_calling", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_module_loads_by_path():
    mod = _load()
    assert hasattr(mod, "main")
    assert hasattr(mod, "post")


def test_default_model_and_host(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    mod = _load(monkeypatch, argv=["check-tool-calling.py"])
    assert mod.MODEL == "llama3.1:8b"
    assert mod.HOST == "http://localhost:11434"


def test_model_arg_and_host_env(monkeypatch):
    mod = _load(
        monkeypatch,
        argv=["check-tool-calling.py", "qwen2.5-coder:14b"],
        env={"OLLAMA_HOST": "http://example:9999/"},
    )
    assert mod.MODEL == "qwen2.5-coder:14b"
    assert mod.HOST == "http://example:9999"  # trailing slash stripped


def test_pass_when_structured_tool_calls(monkeypatch, capsys):
    mod = _load(monkeypatch, argv=["check-tool-calling.py"])
    monkeypatch.setattr(
        mod, "post",
        lambda url, payload: {"message": {"tool_calls": [
            {"function": {"name": "read_file", "arguments": {"path": "sample.txt"}}}]}},
    )
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "read_file" in out


def test_fail_when_no_tool_calls(monkeypatch, capsys):
    mod = _load(monkeypatch, argv=["check-tool-calling.py"])
    monkeypatch.setattr(
        mod, "post",
        lambda url, payload: {"message": {
            "content": '{"name": "read_file", "arguments": {"path": "sample.txt"}}'}},
    )
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "NOT usable" in out


def test_error_when_ollama_unreachable(monkeypatch, capsys):
    mod = _load(monkeypatch, argv=["check-tool-calling.py"])

    def boom(url, payload):
        raise OSError("connection refused")

    monkeypatch.setattr(mod, "post", boom)
    assert mod.main() == 2
    assert "ERROR contacting Ollama" in capsys.readouterr().out
