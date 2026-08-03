"""Coverage tests for check_correction_attribution.py (G-V12).

WHY IT EXISTS (dogfood 2026-08-03). `/corrections-audit` computed the escape
rate by hand. Its headline — "62% were caught by the user, only ~25% by a
hook/evaluator/agent-self" — is the most decision-relevant number the correction
loop produces, because it answers the only question the loop exists to answer:
more harness, or more context. It had been computed twice, six weeks apart, each
time because a human remembered to look.

THE TESTS THAT MATTER HERE ARE THE DENOMINATOR ONES. A rate over 14 of 72
entries is a claim about 19% of the corpus, and quoting it without saying so is
the precise failure this repo spent 2026-08-02/03 removing from its own checks.
Three separate assertions below exist to keep the denominator attached to the
number: it is printed unprompted, the sub-half case is called out explicitly,
and a corpus with no attribution at all refuses to state a rate rather than
reporting 0%.

Scenario-per-guardpost:
  happy   — mixed catchers            -> rate + denominator + coverage
  sad     — none caught by automation -> escape rate 100%, still with denominator
  bad     — no attributions at all    -> NO RATE, not 0%
  bad     — no corrections.md         -> N/A, not an empty pass
  edge    — hook and user in one entry-> first match wins, deterministically
  edge    — coverage below half       -> says so unprompted
"""
import json
import sys

import pytest


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_correction_attribution

    return check_correction_attribution


def _corpus(root, entries):
    d = root / ".claude" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    body = "# Corrections Log\n\n## Generalizable Corrections\n\n"
    for i, (date, text) in enumerate(entries):
        body += f"### {date} - entry {i}\n\n{text}\n\n"
    (d / "corrections.md").write_text(body)
    return root


# ------------------------------------------------------------------ happy


def test_mixed_catchers_are_counted_and_the_rate_is_reported(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _corpus(tmp_path, [
        ("2026-01-01", "This one was caught by hook during CI."),
        ("2026-01-02", "Caught by founder in review of the draft."),
        ("2026-01-03", "agent-self-caught on a second read."),
        ("2026-01-04", "surfaced by user after the send."),
    ])
    st = mod.scan(tmp_path)
    assert st["entries"] == 4
    assert st["attributed"] == 4
    assert st["by_catcher"]["user"] == 2
    assert st["by_catcher"]["hook_or_check"] == 1
    assert st["by_catcher"]["agent_self"] == 1
    # escape = share NOT caught by hook or agent-self = 2/4
    assert st["escape_rate"] == 0.5


# ------------------------------------------------------------------ sad


def test_everything_user_caught_is_a_100_percent_escape_rate(scripts_path, tmp_path):
    """The worst real state, and the one the 2026-06-25 audit was closest to."""
    mod = _import(scripts_path)
    _corpus(tmp_path, [
        ("2026-01-01", "caught by user."),
        ("2026-01-02", "Caught by founder."),
    ])
    st = mod.scan(tmp_path)
    assert st["escape_rate"] == 1.0
    assert st["coverage"] == 1.0


# ------------------------------------------------------------------ bad


def test_no_attributions_refuses_to_state_a_rate(scripts_path, tmp_path, capsys):
    """THE LOAD-BEARING ONE. Zero attributed must not read as a 0% escape rate.

    An unattributed corpus means the loop cannot answer its own question. Saying
    "0%" there would be the best-looking possible number produced by measuring
    nothing — the exact shape of every false green found in this repo this week.
    """
    mod = _import(scripts_path)
    _corpus(tmp_path, [("2026-01-01", "Something went wrong and was fixed.")])
    st = mod.scan(tmp_path)
    assert st["attributed"] == 0
    assert st["escape_rate"] is None, "no data must yield no rate, not a flattering one"
    mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "NO RATE AVAILABLE" in out
    assert "0%" not in out


def test_absent_corrections_file_is_na(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    (tmp_path / ".claude").mkdir(parents=True)
    mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "N/A" in out
    assert "nothing was supposed to be" in out


# ------------------------------------------------------------------ edge


def test_first_match_wins_deterministically(scripts_path, tmp_path):
    """An entry naming two catchers must not be counted twice or vary by run.

    Priority is hook/check before user, because an entry saying the hook caught
    it AND the user confirmed it is a hook catch — crediting it to the user
    would overstate the escape rate, which is the direction that matters.
    """
    mod = _import(scripts_path)
    _corpus(tmp_path, [
        ("2026-01-01", "caught by hook, then surfaced by user in the same pass."),
    ])
    st = mod.scan(tmp_path)
    assert st["by_catcher"] == {"hook_or_check": 1}
    assert st["escape_rate"] == 0.0


def test_the_denominator_is_always_printed(scripts_path, tmp_path, capsys):
    """A rate without its denominator is the failure this file exists to prevent."""
    mod = _import(scripts_path)
    _corpus(tmp_path, [
        ("2026-01-01", "caught by hook."),
        ("2026-01-02", "no attribution here at all."),
        ("2026-01-03", "nor here."),
    ])
    mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "measured over 1 of 3 entries" in out
    assert "coverage" in out
    assert "2 carry no catcher" in out


def test_coverage_below_half_says_so(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    _corpus(tmp_path, [
        ("2026-01-01", "caught by hook."),
        ("2026-01-02", "unattributed."),
        ("2026-01-03", "unattributed."),
    ])
    mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert "COVERAGE IS BELOW HALF" in out
    assert "indicative, not" in out


def test_real_corpus_parses(scripts_path):
    """The live gate: the shipped corrections.md must produce a usable read."""
    mod = _import(scripts_path)
    st = mod.scan(scripts_path.parents[2])
    assert st["applicable"] is True
    assert st["entries"] > 0
    if st["attributed"]:
        assert 0.0 <= st["escape_rate"] <= 1.0
        assert st["coverage"] is not None


@pytest.mark.parametrize(("phrase", "expected"), [
    ("caught by hook", "hook_or_check"),
    ("found by the validator", "hook_or_check"),
    ("flagged by CI", "hook_or_check"),
    ("Caught by founder", "user"),
    ("surfaced by the user", "user"),
    ("caught by the review", "review"),
    ("self-caught", "agent_self"),
])
def test_phrasings_already_in_the_corpus_are_recognised(scripts_path, phrase, expected):
    """The parser meets the corpus where it is.

    These forms were counted in the live corrections.md before this script
    existed. A structured field would be cleaner and would invalidate every one
    of them, so the vocabulary is derived rather than imposed.
    """
    mod = _import(scripts_path)
    assert mod.classify(f"Some text. {phrase}. More text.") == expected


# ------------------------------------------------- both entry formats (v0.80.1)
# corrections.md uses TWO shapes and this script read one of them, so its own
# denominator was wrong. Found the first time it ran against a freshly-appended
# log: five new entries, every one carrying an explicit "Caught by ..." phrase,
# were invisible, and the tool printed "measured over 14 of 74" while the corpus
# held ~101. A wrong denominator inside the script written to print honest
# denominators.


def _bullet_corpus(root, lines):
    d = root / ".claude" / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / "corrections.md").write_text("# Corrections Log\n\n" + "\n\n".join(lines) + "\n")
    return root


def test_bullet_style_entries_are_counted(scripts_path, tmp_path):
    """`- **Title (YYYY-MM-DD, class)**: ...` is what recent entries actually use."""
    mod = _import(scripts_path)
    root = _bullet_corpus(tmp_path, [
        "- **Something went wrong (2026-08-03, some-class)**: prose. Caught by founder.",
        "- **Another thing (2026-08-02, other-class)**: prose. Caught by hook.",
    ])
    result = mod.scan(root)
    assert result["entries"] == 2, result
    assert result["attributed"] == 2, result


def test_heading_and_bullet_entries_interleave(scripts_path, tmp_path):
    """A body must run to whichever entry starts next, whichever form it takes.
    If the two formats did not share one scan, a heading body would swallow every
    bullet after it and their catchers would be credited to the wrong entry."""
    mod = _import(scripts_path)
    d = tmp_path / ".claude" / "memory"
    d.mkdir(parents=True)
    (d / "corrections.md").write_text(
        "# Corrections Log\n\n"
        "### 2026-05-01 - heading entry\n\nprose. Caught by the user.\n\n"
        "- **Bullet entry (2026-05-02, cls)**: prose. Caught by the hook.\n\n"
        "### 2026-05-03 - another heading\n\nprose with no catcher at all.\n\n"
        "- **Last bullet (2026-05-04, cls)**: prose. Self-caught by the agent.\n"
    )
    result = mod.scan(tmp_path)
    assert result["entries"] == 4, result
    assert result["attributed"] == 3, result
    assert result["by_catcher"]["user"] == 1
    assert result["by_catcher"]["hook_or_check"] == 1
    assert result["by_catcher"]["agent_self"] == 1


def test_bullet_without_a_date_is_not_an_entry(scripts_path, tmp_path):
    """EDGE. Ordinary bulleted prose inside an entry body must not split it —
    the file is full of `- **Prevention**:` style lines."""
    mod = _import(scripts_path)
    root = _bullet_corpus(tmp_path, [
        "- **Real entry (2026-08-03, cls)**: prose. Caught by founder.",
        "- **Prevention**: do the thing. Not an entry, no date.",
        "- some plain bullet",
    ])
    result = mod.scan(root)
    assert result["entries"] == 1, result


# ------------------------------------------------- snapshot series (v0.81.0)
# The rate existed only as prose in hand-written TL;DR paragraphs — three
# readings across two months, each recomputed by someone who remembered to look,
# and the top-of-file count was stale by 46 entries when this was added. A rate
# whose trend cannot be computed answers the wrong question.


def test_snapshot_writes_the_metrics_envelope(scripts_path, tmp_path):
    mod = _import(scripts_path)
    root = _corpus(tmp_path, [("2026-05-01", "prose. Caught by the user."),
                              ("2026-05-02", "prose. Caught by the hook.")])
    out = tmp_path / "series"
    path = mod.write_snapshot(root, mod.scan(root), out)
    assert path is not None and path.is_file()
    d = json.loads(path.read_text())
    # Matches the existing .claude/evals/metrics/<source>/<date>.json shape
    # rather than inventing a second convention.
    for key in ("pulled_at", "source", "source_class", "target",
                "adapter_version", "fetch_status", "primary_counts"):
        assert key in d, f"missing envelope key {key}"
    assert d["source"] == "corrections"
    assert d["primary_counts"]["entries"] == 2
    assert d["primary_counts"]["caught_by_hook_or_check"] == 1
    assert d["escape_rate"] == 0.5


def test_snapshot_refuses_when_there_is_no_rate(scripts_path, tmp_path):
    """Storing a null in a series is how a gap becomes a number later."""
    mod = _import(scripts_path)
    root = _corpus(tmp_path, [("2026-05-01", "prose with no catcher named.")])
    out = tmp_path / "series"
    assert mod.write_snapshot(root, mod.scan(root), out) is None
    assert not out.exists(), "no directory should be created for a non-reading"


def test_same_day_rerun_overwrites_rather_than_duplicating(scripts_path, tmp_path):
    """A snapshot is a state-of-day reading, not an event log."""
    mod = _import(scripts_path)
    root = _corpus(tmp_path, [("2026-05-01", "prose. Caught by the user.")])
    out = tmp_path / "series"
    first = mod.write_snapshot(root, mod.scan(root), out)
    second = mod.write_snapshot(root, mod.scan(root), out)
    assert first == second
    assert len(list(out.glob("*.json"))) == 1


def test_snapshot_is_opt_in(scripts_path, tmp_path, capsys):
    """Reporting must not have a filesystem side effect unless asked."""
    mod = _import(scripts_path)
    root = _corpus(tmp_path, [("2026-05-01", "prose. Caught by the user.")])
    mod.main(["--root", str(root)])
    capsys.readouterr()
    assert not (root / mod.SNAPSHOT_REL).exists()


def test_snapshot_happens_for_both_output_formats(scripts_path, tmp_path, capsys):
    """v0.77.0 found five scripts whose behaviour differed between --json and
    plain because the work lived inside one arm of the output branch."""
    mod = _import(scripts_path)
    for as_json in (False, True):
        root = _corpus(tmp_path / f"r{as_json}",
                       [("2026-05-01", "prose. Caught by the user.")])
        argv = ["--root", str(root), "--snapshot"]
        if as_json:
            argv.append("--json")
        mod.main(argv)
        capsys.readouterr()
        written = list((root / mod.SNAPSHOT_REL).glob("*.json"))
        assert len(written) == 1, f"as_json={as_json} wrote {written}"
