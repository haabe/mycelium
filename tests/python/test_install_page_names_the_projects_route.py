"""The install page tells a Claude Code Projects user where the plugin has to be added.

Candidate claude-code-projects-cloud-threads-do-not-load-a-repo-enabled-plugin (founder ruling
2026-11-12, "add the Projects install paragraph"): Claude Code's Projects documentation says a cloud
thread does not load a plugin a repository enables, so a user who moves into a Project loses every
hook with no message. The page says where to add it, says the source is Anthropic's documentation,
and says that hooks firing after the Project-settings route has not been checked.
"""

from __future__ import annotations

from pathlib import Path

PAGE = Path(__file__).resolve().parents[2] / "docs" / "install-paths.md"


def test_install_page_names_project_settings_route_and_its_limit():
    text = " ".join(PAGE.read_text(encoding="utf-8").split())
    assert "### In a Claude Code Project (cloud threads)" in text
    assert "**Project settings > Plugins**" in text
    assert "Claude Code's Projects documentation" in text
    assert "has not been checked" in text
