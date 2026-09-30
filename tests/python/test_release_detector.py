"""What the release gate counts as a release (v0.290.0, phase migration stage 0b-1).

Three changes, each with its control: tunnels count; a plain `git push` counts when the project's host
publishes what is pushed; and text that is only carried by a command (a heredoc body, a commit
message, an echo) no longer counts, while text that is executed (ssh, bash -c) still does. The gate
refused two documentation edits on 2026-09-30 because their heredocs mentioned a release verb.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import scale_locks as sl  # noqa: E402

REL = "fly " + "deploy"  # split so this file does not trip the release gate's own prose match


def _is_release(cmd: str) -> bool:
    return bool(sl._DEPLOY.search(sl._executed_text(cmd)))


@pytest.mark.parametrize("cmd", [
    REL + " --app cadence",
    "bash -c '" + REL + "'",
    'sh -c "' + REL + '"',
    "ssh app@host 'cd app && git pull && systemctl restart cadence'",
    "ngrok http 8000",
    "cloudflared tunnel run cadence",
    "tailscale funnel 8000",
    "ssh -R 80:localhost:8000 serveo.net",
])
def test_these_are_releases(cmd):
    assert _is_release(cmd)


@pytest.mark.parametrize("cmd", [
    "git commit -m 'next: " + REL + " once the gates pass'",
    "cat > notes.md <<'EOF'\nwe will " + REL + " after review\nEOF\ngit add notes.md",
    "echo '" + REL + "'",
    "python3 -c \"print('" + REL + "')\"",
    "npm test",
])
def test_prose_that_only_mentions_a_release_is_not_one(cmd):
    assert not _is_release(cmd)


def test_a_push_counts_when_the_host_publishes_what_is_pushed(tmp_path):
    (tmp_path / "vercel.json").write_text("{}\n")
    assert sl._goes_live_on_push(str(tmp_path))


def test_a_push_counts_when_a_workflow_deploys_on_push(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "pages.yml").write_text("on:\n  push:\n    branches: [main]\njobs:\n  d:\n    steps:\n"
                                  "      - uses: actions/deploy-pages@v4\n")
    assert sl._goes_live_on_push(str(tmp_path))


def test_control_a_push_with_no_publishing_host_is_not_a_release(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text("on:\n  push:\njobs:\n  t:\n    steps:\n      - run: pytest\n")
    assert not sl._goes_live_on_push(str(tmp_path))
