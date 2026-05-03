"""Shared fixtures for Mycelium Python script tests."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project dir with .claude/manifest.yml + state/."""
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def upstream_state(project_dir):
    """Write an active upstream.json to the project's state directory."""
    state_file = project_dir / ".claude" / "state" / "upstream.json"
    state_file.write_text(json.dumps({
        "upstream_repo": "/path/to/upstream",
        "active": True,
    }))
    return state_file


@pytest.fixture
def manifest_yaml():
    """Standard manifest.yml content used across tests."""
    return """\
framework:
  top_level:
    - CLAUDE.md
    - README.md
    - AGENTS.md
  directories:
    - .claude/skills/
    - .claude/hooks/
    - .claude/engine/
    - .claude/scripts/
  single_files:
    - .claude/manifest.yml
harness_framework:
  - .claude/harness/guardrails.md
  - .claude/harness/security-trust.md
project_state:
  - .claude/memory/
  - .claude/canvas/
  - .claude/state/
preserved_dir_readmes:
  - .claude/canvas/README.md
  - .claude/memory/README.md
evals:
  replace:
    - .claude/evals/scenarios/
metrics_adapters:
  framework:
    - .claude/jit-tooling/metrics-adapters/github.md
"""


@pytest.fixture
def manifest_path(project_dir, manifest_yaml):
    """Write the standard manifest.yml to the project."""
    path = project_dir / ".claude" / "manifest.yml"
    path.write_text(manifest_yaml)
    return path


@pytest.fixture
def scripts_path():
    """Path to the .claude/scripts/ directory containing the modules under test."""
    # Tests live at .claude/tests/python/conftest.py — scripts are at
    # .claude/scripts/. Resolve via the test file's location.
    here = Path(__file__).resolve()
    return here.parent.parent.parent / "scripts"
