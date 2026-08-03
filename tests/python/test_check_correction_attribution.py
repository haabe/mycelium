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
