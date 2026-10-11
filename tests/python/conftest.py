"""Shared fixtures for Mycelium Python script tests."""
import json
from pathlib import Path

import _scratch_git
import pytest

# THE SUITE DOES NOT INHERIT A REPOSITORY FROM WHOEVER STARTED IT (0.319.1).
# git exports GIT_DIR to a hook when the push or commit comes from a worktree, and a `git init`
# in a temp folder then re-initialises the CALLER'S repository, `git config` writes its config and
# `git commit` lands on its branch. Until 0.319.1 nothing here cleared it: on 2026-10-11 a push
# from a worktree left fourteen fixture commits on a feature branch and `core.bare = true` in the
# shared config. Cleared at import, which is before collection and once per xdist worker; the
# full account and the second layer are in _scratch_git.py.
_scratch_git.clear_inherited_git_env()


def pytest_configure(config):
    # 2026-09-25: the three whole-repo scans (check_wiring_contract, check_test_authenticity,
    # check_wiring on the shipped tree) are ~110 s of a ~150 s suite. CI runs them in its parallel
    # pytest job, where they are the enforcement point; the fast pre-push tier deselects them with
    # `-m "not realrepo"`.
    config.addinivalue_line("markers", "realrepo: scans the whole shipped repo (slow; CI enforces)")


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
    """Path to the plugins/mycelium/scripts/ directory containing the modules under test."""
    # Tests live at <repo>/tests/python/conftest.py post-2026-05-09 legacy
    # cleanup; scripts are at <repo>/plugins/mycelium/scripts/. Previously
    # the layout was .claude/tests/python/ and .claude/scripts/ as siblings.
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent
    return repo_root / "plugins" / "mycelium" / "scripts"
