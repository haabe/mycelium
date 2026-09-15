"""Coverage proof for check_evidence_links.py (shipped upstream 0.205.0 from the dogfood tree).

No test here touches the network: `_urlopen` is replaced with a fake that answers per URL.
The three design rules from the module docstring are each pinned by a test that plants the
opposite and requires it NOT to happen: a transient failure must not read as rot, a bot wall
must not read as a dead page, and one 404 must not escalate without a second day.
"""

from __future__ import annotations

import datetime
import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "plugins/mycelium/scripts/check_evidence_links.py"


def _mod():
    spec = importlib.util.spec_from_file_location("cel", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["cel"] = m
    spec.loader.exec_module(m)
    return m


class _Resp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_urlopen(table):
    """table: url -> int status | Exception instance. Unknown urls answer 200."""
    def fake(req, timeout):
        url = req.full_url
        ans = table.get(url, 200)
        if isinstance(ans, Exception):
            raise ans
        if ans == 200:
            return _Resp()
        raise urllib.error.HTTPError(url, ans, "x", {}, io.BytesIO(b""))
    return fake


def _project(tmp_path, files):
    root = tmp_path / "proj"
    (root / ".claude" / "canvas").mkdir(parents=True)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _run(mod, root, *extra, today="2026-09-14"):
    return mod.main(["--project-dir", str(root), "--today", today, "--force", "--workers", "1", *extra])


def _snapshot(mod, root, day):
    data = json.loads((root / mod.SNAP_REL / f"{day}.json").read_text())
    return data["urls"]


# ---------------------------------------------------------------- collection

def test_collect_finds_citations_and_skips_illustrations(tmp_path):
    mod = _mod()
    root = _project(tmp_path, {
        ".claude/canvas/landscape.yml": (
            "url: https://example.org/a\n"            # reserved: an illustration
            "url: https://api.stripe.com/v1/charges\n"  # api host: wants a key
            "url: https://site.test/x\n"               # reserved TLD
            "url: https://blog.example-real.com/post?q=1\n"
            "code: `https://blog.example-real.com/post?q=1`\n"  # backtick stripped, same url
            "tmpl: https://host.com/$VAR/x\n"          # placeholder
        ),
        "docs/notes.md": "_see https://blog.example-real.com/other_ and https://gone.example-real.com/p.",
    })
    mod.ROOT = root
    cited = mod.collect()
    assert set(cited) == {"https://blog.example-real.com/post?q=1",
                          "https://blog.example-real.com/other",
                          "https://gone.example-real.com/p"}
    assert cited["https://blog.example-real.com/post?q=1"] == [".claude/canvas/landscape.yml"]


# ---------------------------------------------------------------- the three rules

def test_a_transient_failure_is_unknown_not_rot(tmp_path, monkeypatch, capsys):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://a.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://a.example-real.com/x": 503}))
    assert _run(mod, root) == 0
    assert _snapshot(mod, root, "2026-09-14")["https://a.example-real.com/x"]["status"] == mod.UNKNOWN
    assert "could not be checked" in capsys.readouterr().out


def test_a_bot_wall_is_blocked_and_asks_for_a_browser(tmp_path, monkeypatch, capsys):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://wall.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://wall.example-real.com/x": 403}))
    _run(mod, root)
    rec = _snapshot(mod, root, "2026-09-14")["https://wall.example-real.com/x"]
    assert rec["status"] == mod.BLOCKED and rec["needs_browser_check"] is True
    assert "ASK: these need a look in the browser" in capsys.readouterr().out


def test_one_404_is_pending_and_a_second_day_makes_it_rotted(tmp_path, monkeypatch, capsys):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://gone.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://gone.example-real.com/x": 404}))
    _run(mod, root, today="2026-09-14")
    assert _snapshot(mod, root, "2026-09-14")["https://gone.example-real.com/x"]["status"] == mod.PENDING
    # a same-day re-run must NOT count as the second strike
    _run(mod, root, today="2026-09-14")
    assert _snapshot(mod, root, "2026-09-14")["https://gone.example-real.com/x"]["status"] == mod.PENDING
    rc = _run(mod, root, "--strict", today="2026-09-15")
    assert rc == 1
    assert _snapshot(mod, root, "2026-09-15")["https://gone.example-real.com/x"]["status"] == mod.ROTTED
    assert "ROTTED — failed on two consecutive runs" in capsys.readouterr().out


def test_github_404_confirmed_by_the_api_is_ok(tmp_path, monkeypatch):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://github.com/o/r/commit/abc123\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({
        "https://github.com/o/r/commit/abc123": 404,
        "https://api.github.com/repos/o/r/commits/abc123": 200,
    }))
    _run(mod, root)
    rec = _snapshot(mod, root, "2026-09-14")["https://github.com/o/r/commit/abc123"]
    assert rec["status"] == mod.OK and "GitHub API confirms" in rec["detail"]


def test_github_404_the_api_cannot_settle_is_unknown(tmp_path, monkeypatch):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://github.com/o/r/issues/7\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({
        "https://github.com/o/r/issues/7": 404,
        "https://api.github.com/repos/o/r/issues/7": 503,
    }))
    _run(mod, root)
    assert _snapshot(mod, root, "2026-09-14")["https://github.com/o/r/issues/7"]["status"] == mod.UNKNOWN


# ---------------------------------------------------------------- browser verdicts

def test_a_browser_verdict_outranks_the_probe(tmp_path, monkeypatch):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://gone.example-real.com/x\nv: https://dead.example-real.com/y\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://gone.example-real.com/x": 404,
                                                          "https://dead.example-real.com/y": 403}))
    assert mod.main(["--project-dir", str(root), "--today", "2026-09-14",
                     "--mark-verified", "https://gone.example-real.com/x", "--verdict", "ok", "--note", "saw it"]) == 0
    assert mod.main(["--project-dir", str(root), "--today", "2026-09-14",
                     "--mark-verified", "https://dead.example-real.com/y", "--verdict", "gone"]) == 0
    _run(mod, root)
    snap = _snapshot(mod, root, "2026-09-14")
    assert snap["https://gone.example-real.com/x"]["status"] == mod.OK
    assert snap["https://dead.example-real.com/y"]["status"] == mod.ROTTED   # no second strike needed


def test_a_corrupt_verified_store_is_reported_not_emptied_silently(tmp_path, capsys):
    mod = _mod()
    root = _project(tmp_path, {})
    mod.ROOT = root
    vf = mod.verified_file()
    vf.parent.mkdir(parents=True)
    vf.write_text("{not json")
    assert mod.load_verified() == {}
    assert "is unreadable" in capsys.readouterr().err


# ---------------------------------------------------------------- throttle and preconditions

def test_recent_snapshot_throttles_unless_forced(tmp_path, monkeypatch, capsys):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://a.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({}))
    _run(mod, root, today="2026-09-10")
    rc = mod.main(["--project-dir", str(root), "--today", "2026-09-14", "--workers", "1"])
    assert rc == 0
    assert "skipped — last run 4d ago" in capsys.readouterr().out
    assert not (root / mod.SNAP_REL / "2026-09-14.json").exists()


def test_no_claude_dir_is_a_refusal_not_a_pass(tmp_path, capsys):
    mod = _mod()
    assert mod.main(["--project-dir", str(tmp_path / "nowhere")]) == 2
    assert "NOT A PASS" in capsys.readouterr().out


def test_no_urls_says_so(tmp_path, capsys):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "no links here\n"})
    assert _run(mod, root) == 0
    assert "no urls found" in capsys.readouterr().out


def test_framework_root_is_announced_when_missing(tmp_path, capsys, monkeypatch):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://a.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({}))
    _run(mod, root, "--include-framework")
    assert "no framework tree found" in capsys.readouterr().out


def test_non_http_schemes_are_refused_at_the_call(tmp_path):
    mod = _mod()
    with pytest.raises(ValueError, match="non-http"):
        mod._request("file:///etc/passwd", {})


def test_a_yaml_escape_dragged_into_the_url_is_stripped(tmp_path):
    """First upstream run, 2026-09-14: a double-quoted YAML scalar ending in \\n produced a URL
    ending in a literal backslash-n, which 404s while the real page is fine."""
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/h.yml": 'note: "see https://github.com/o/r\\n and more"\n'})
    mod.ROOT = root
    assert set(mod.collect()) == {"https://github.com/o/r"}


# --- 0.205.1: two cases the dogfood tree pinned that the port had not ----------------------


def test_browser_unclear_stays_unknown(tmp_path, monkeypatch):
    """A human looked and still could not tell. Forcing ok or gone would invent an answer."""
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://gone.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://gone.example-real.com/x": 404}))
    assert mod.main(["--project-dir", str(root), "--today", "2026-09-14",
                     "--mark-verified", "https://gone.example-real.com/x", "--verdict", "unclear"]) == 0
    _run(mod, root)
    rec = _snapshot(mod, root, "2026-09-14")["https://gone.example-real.com/x"]
    assert rec["status"] == mod.UNKNOWN
    assert rec["needs_browser_check"] is False


def test_a_stale_browser_verdict_is_asked_for_again(tmp_path, monkeypatch):
    mod = _mod()
    root = _project(tmp_path, {".claude/canvas/c.yml": "u: https://wall.example-real.com/x\n"})
    monkeypatch.setattr(mod, "_urlopen", _fake_urlopen({"https://wall.example-real.com/x": 403}))
    mod.ROOT = root
    mod.mark_verified("https://wall.example-real.com/x", "ok", "", datetime.date(2020, 1, 1))
    _run(mod, root)
    rec = _snapshot(mod, root, "2026-09-14")["https://wall.example-real.com/x"]
    assert rec["status"] == mod.BLOCKED
    assert rec["needs_browser_check"] is True
