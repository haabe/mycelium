"""The release backstop reads every release, not the newest 500 (v0.325.2).

WHAT WAS WRONG, 2026-10-15. `release_gaps.py` listed releases with `gh release list --limit
500`, newest first. The merge of v0.325.1 made the 501st release; the release was published, and
the step after it, `release_gaps.py --check`, failed with "1 documented version(s) have no GitHub
Release: v0.49.19". v0.49.19 was published on 2026-06-19. It was the oldest release at or above
the check's floor (v0.49.0), and the list stopped one short of it. The release audit and the
manual repair read the same list, so the repair would have tried to create it again.

The fake `gh` below holds more releases than the old limit and answers both the old call and the
new one honestly, so these tests are red on the old code.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "plugins" / "mycelium" / "scripts"))

import release_gaps as rg  # noqa: E402

OLD_LIMIT = 500
TAGS = [f"v0.{n}.0" for n in range(OLD_LIMIT + 1, 0, -1)]  # newest first, one past the limit

FAKE_GH = """#!/usr/bin/env python3
import json, sys
tags = json.load(open({tags!r}))
args = sys.argv[1:]
if args[:2] == ["release", "list"]:
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 30
    print(json.dumps([{{"tagName": t}} for t in tags[:limit]]))
elif args[:1] == ["api"] and "--paginate" in args:
    print("\\n".join(tags))
elif args[:1] == ["api"]:
    print("\\n".join(tags[:30]))
else:
    sys.exit("fake gh: unexpected call " + " ".join(args))
"""


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch) -> Path:
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps(TAGS))
    gh = tmp_path / "bin" / "gh"
    gh.parent.mkdir()
    gh.write_text(FAKE_GH.format(tags=str(tags)))
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{gh.parent}{os.pathsep}{os.environ['PATH']}")
    return gh


def test_the_oldest_release_past_the_old_limit_is_listed(fake_gh):
    """RED ON 0.325.1: the list stopped at 500 and the oldest release was not in it."""
    released = rg._released_from_gh()
    assert len(released) == len(TAGS)
    assert "0.1.0" in released


def test_a_documented_release_past_the_old_limit_is_not_a_gap(fake_gh):
    """The failure as the backstop showed it: a published release read as missing."""
    documented = ["0.1.0", "0.2.0", f"0.{OLD_LIMIT + 1}.0"]
    assert rg.missing_releases(documented, rg._released_from_gh(), "0.0.0") == []


def test_an_unreadable_release_list_still_exits_2(tmp_path, monkeypatch, capsys):
    gh = tmp_path / "bin" / "gh"
    gh.parent.mkdir()
    gh.write_text("#!/bin/sh\necho 'HTTP 401: Bad credentials' >&2\nexit 1\n")
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{gh.parent}{os.pathsep}{os.environ['PATH']}")
    with pytest.raises(SystemExit) as exit_:
        rg._released_from_gh()
    assert exit_.value.code == 2
    assert "could not list releases" in capsys.readouterr().err
