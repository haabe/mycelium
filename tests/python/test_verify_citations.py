"""Coverage proofs for verify_citations.py.

Per G-V12: every check ships with a test demonstrating it does what it claims.
verify_citations.py attacks anti-pattern #7 Level 3 (fabricated underlying
inputs in `(per: <source>)` citations). The test contract:

- File-shaped citations with matching reads → verified
- File-shaped citations WITHOUT matching reads → unverified (the signal we want)
- Concept-shaped citations → unverifiable (out of scope by design)
- Path-shape heuristics handle absolute/relative/anchored citations
- Suffix matching: citation `landscape.yml` matches read of `/abs/path/landscape.yml`
"""
import io
import json
import sys
from pathlib import Path

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import verify_citations  # noqa: PLC0415
    return verify_citations


@pytest.fixture
def vc():
    scripts_path = Path(__file__).resolve().parents[2] / "plugins" / "mycelium" / "scripts"
    return _import(scripts_path)


@pytest.fixture
def read_log(tmp_path):
    """Build a read-log.jsonl fixture with three reads in one session."""
    log = tmp_path / "read-log.jsonl"
    entries = [
        {"ts": "2026-05-11T19:00:00Z", "tool": "Read", "file_path": "/Users/x/repo/.claude/canvas/landscape.yml", "session_id": "s1"},
        {"ts": "2026-05-11T19:01:00Z", "tool": "Read", "file_path": "/Users/x/repo/.claude/canvas/purpose.yml", "session_id": "s1"},
        {"ts": "2026-05-11T19:02:00Z", "tool": "Read", "file_path": "/Users/x/repo/CLAUDE.md", "session_id": "s1"},
        {"ts": "2026-05-11T19:03:00Z", "tool": "Read", "file_path": "/other/session/file.md", "session_id": "s2"},
    ]
    with open(log, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return log


def test_file_shape_heuristic(vc):
    """Heuristic correctly classifies file-shaped vs concept-shaped sources."""
    assert vc.looks_like_file_path("landscape.yml")
    assert vc.looks_like_file_path(".claude/canvas/purpose.yml")
    assert vc.looks_like_file_path("docs/receipts/cases/2026-05-08-bentes.md")
    assert vc.looks_like_file_path("/Users/x/CLAUDE.md")
    assert vc.looks_like_file_path("landscape.yml#strategic_frame")  # anchor stripped for shape

    assert not vc.looks_like_file_path("L2 Discover gate")
    assert not vc.looks_like_file_path("Torres CDH")
    assert not vc.looks_like_file_path("corrections cluster #7")
    assert not vc.looks_like_file_path("prior decision-log entry")


def test_extract_citations_basic(vc):
    text = "Recommending /threat-model (per: L4 deliver gate + threat-model.yml stale 47 days)."
    cites = list(vc.extract_citations(text))
    assert len(cites) == 1
    assert cites[0]["file_shaped"] is True  # "threat-model.yml" makes it file-shaped


def test_extract_citations_multiple_dedup(vc):
    text = (
        "Per the rule (per: landscape.yml). And again (per: landscape.yml). "
        "Different (per: purpose.yml#trajectory). Concept (per: Torres CDH)."
    )
    cites = list(vc.extract_citations(text))
    assert len(cites) == 3  # deduped
    sources = [c["source"] for c in cites]
    assert "landscape.yml" in sources
    assert "purpose.yml#trajectory" in sources
    assert "Torres CDH" in sources


def test_suffix_match(vc):
    """Citation `landscape.yml` matches read of `/abs/path/.claude/canvas/landscape.yml`."""
    assert vc.cited_path_matches_read("landscape.yml", "/Users/x/repo/.claude/canvas/landscape.yml")
    assert vc.cited_path_matches_read(".claude/canvas/landscape.yml", "/Users/x/repo/.claude/canvas/landscape.yml")
    assert vc.cited_path_matches_read("CLAUDE.md", "/Users/x/repo/CLAUDE.md")
    # Anchors stripped before matching
    assert vc.cited_path_matches_read("landscape.yml#strategic_frame", "/Users/x/repo/.claude/canvas/landscape.yml")


def test_suffix_match_no_false_positive(vc):
    """`scape.yml` shouldn't match `landscape.yml` (must be path-boundary aligned)."""
    assert not vc.cited_path_matches_read("scape.yml", "/Users/x/repo/.claude/canvas/landscape.yml")
    assert not vc.cited_path_matches_read("foo.yml", "/Users/x/repo/.claude/canvas/landscape.yml")


def test_verify_all_verified(vc, read_log):
    text = "I checked (per: landscape.yml) and (per: purpose.yml) and (per: CLAUDE.md)."
    entries = vc.load_read_log(read_log)
    report = vc.verify(text, entries)
    assert report["total_citations"] == 3
    assert report["file_shaped"] == 3
    assert len(report["verified"]) == 3
    assert len(report["unverified"]) == 0


def test_verify_unverified_caught(vc, read_log):
    """The load-bearing test: file-citation with no matching read = signal."""
    text = "Based on (per: landscape.yml) and (per: opportunities.yml)."
    # opportunities.yml is NOT in the read-log fixture
    entries = vc.load_read_log(read_log)
    report = vc.verify(text, entries)
    assert len(report["verified"]) == 1
    assert len(report["unverified"]) == 1
    assert "opportunities.yml" in report["unverified"]


def test_verify_concept_citations_unverifiable(vc, read_log):
    """Concept-shaped citations route to unverifiable (not unverified)."""
    text = "Suggesting devil's advocate (per: L4 deliver gate). Following (per: Torres CDH)."
    entries = vc.load_read_log(read_log)
    report = vc.verify(text, entries)
    assert report["total_citations"] == 2
    assert report["file_shaped"] == 0
    assert report["concept_shaped"] == 2
    assert len(report["unverified"]) == 0  # no false positives on concepts


def test_session_id_filter(vc, read_log):
    """Filtering to session s1 excludes the s2 read."""
    entries_all = vc.load_read_log(read_log)
    entries_s1 = vc.load_read_log(read_log, session_id_filter="s1")
    entries_s2 = vc.load_read_log(read_log, session_id_filter="s2")
    assert len(entries_all) == 4
    assert len(entries_s1) == 3
    assert len(entries_s2) == 1


def test_missing_read_log_fail_open(vc, tmp_path):
    """Nonexistent read-log returns empty list, doesn't raise."""
    entries = vc.load_read_log(tmp_path / "does-not-exist.jsonl")
    assert entries == []


def test_malformed_jsonl_fail_open(vc, tmp_path):
    """Malformed lines in read-log are skipped, not fatal."""
    log = tmp_path / "read-log.jsonl"
    with open(log, "w") as f:
        f.write('{"ts": "2026-05-11T19:00:00Z", "tool": "Read", "file_path": "/a.md", "session_id": "s1"}\n')
        f.write('not-json-at-all\n')
        f.write('{"ts": "2026-05-11T19:01:00Z", "tool": "Read", "file_path": "/b.md", "session_id": "s1"}\n')
    entries = vc.load_read_log(log)
    assert len(entries) == 2  # malformed line skipped


def test_anti_pattern_7_level_3_scenario(vc, read_log):
    """End-to-end: agent claims to have read a file it didn't read.

    This is the load-bearing scenario the script was built for. The 2026-05-09
    instance #4 of anti-pattern #7 was exactly this shape: agent recommended
    Wardley map work claiming `landscape.yml` was incomplete without actually
    reading it. With the read-log + verify_citations, the unverified citation
    would have surfaced as a signal.
    """
    text = (
        "Wardley Map: Missing (per: landscape.yml). "
        "Recommending /wardley-map (per: theory-gates.md + L1 evidence buckets empty)."
    )
    # Simulate session where landscape.yml was NOT read but a different file was
    entries = [
        {"ts": "2026-05-11T19:00:00Z", "tool": "Read", "file_path": "/Users/x/repo/.claude/diamonds/active.yml", "session_id": "s1"},
    ]
    report = vc.verify(text, entries)
    # landscape.yml citation is unverified — signal
    # theory-gates.md citation is also unverified — signal
    assert "landscape.yml" in report["unverified"]
    assert any("theory-gates.md" in u for u in report["unverified"])
    # No verified file-citations in this session
    assert len(report["verified"]) == 0


def test_format_human_readable(vc):
    """Human-format output is non-empty and includes the unverified set."""
    report = {
        "total_citations": 2,
        "file_shaped": 1,
        "concept_shaped": 1,
        "verified": [],
        "unverified": ["landscape.yml"],
        "unverifiable": ["Torres CDH"],
        "reads_in_session": 5,
    }
    out = vc.format_human(report)
    assert "Citation verification" in out
    assert "landscape.yml" in out
    assert "anti-pattern #7" in out  # explicit linkage to the rule it attacks


def test_main_stdin_json_output(vc, read_log, monkeypatch, capsys):
    """Main entrypoint with --json emits structured JSON."""
    text = "Per (per: landscape.yml) and (per: missing.yml)."
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    monkeypatch.setattr("sys.argv", [
        "verify_citations.py",
        "--read-log", str(read_log),
        "--json",
    ])
    vc.main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_citations"] == 2
    assert "landscape.yml" in data["verified"]
    assert "missing.yml" in data["unverified"]
