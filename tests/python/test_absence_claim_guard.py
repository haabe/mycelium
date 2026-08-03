"""G-V12 coverage proof for absence_claim_guard.py.

THE GAP IT CLOSES. On 2026-08-04 the dogfood project produced five findings of
one shape in a single session: a narrow read promoted to a broad claim without
the promotion being noticed. Two reached the canvas and were pushed before being
caught. There was already an auto-memory rule against exactly this. It did not
fire — notes are read at session start and decay. Every catch came from
re-reading, prompted by the operator; no check caught any of them.

CALIBRATION IS PART OF THE CONTRACT, so it is tested rather than asserted. The
first draft fired on 373 of 88,939 real corpus sentences (0.42%), and roughly
half were ledger prose — "No confidence gate moved", "no skill or framework
change applied" — records of what a session DID, which are true when written and
need no search behind them. Requiring an existence or coverage verb cut it to
113 (0.127%). The ledger cases below are regression fixtures for that.

Scenario-per-guardpost:
  happy — ordinary canvas prose                     -> silence
  happy — an absence claim that names its search    -> silence
  sad   — the 2026-08-04 sentence, verbatim         -> warn
  sad   — "nothing in the framework distinguishes"  -> warn
  sad   — "has never been routed"                   -> warn
  edge  — ledger prose ("No confidence gate moved") -> silence (calibration)
  edge  — a non-watched path                        -> silence
  edge  — Edit uses new_string, not content         -> warn
  edge  — several claims in one write               -> all quoted, capped at 3
  bad   — unparseable payload                       -> silence, exit 0 (fail open)
  bad   — payload with no file_path                 -> silence, exit 0
"""

import json
import subprocess
import sys

import pytest

SCRIPT = "absence_claim_guard.py"
CANVAS = "/Users/x/proj/.claude/canvas/user-needs.yml"


def _run(scripts_path, payload):
    return subprocess.run(
        [sys.executable, str(scripts_path / SCRIPT)],
        input=payload, capture_output=True, text=True, check=False,
    )


def _write(text, path=CANVAS, tool="Write"):
    key = "content" if tool == "Write" else "new_string"
    return json.dumps({"tool_name": tool, "tool_input": {"file_path": path, key: text}})


def _warn(scripts_path, text, path=CANVAS, tool="Write"):
    r = _run(scripts_path, _write(text, path, tool))
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


# ---------------------------------------------------------------- happy


def test_ordinary_canvas_prose_is_silent(scripts_path):
    assert _warn(scripts_path, "confidence 0.45 holds; Bentes drove the ship.") == ""


def test_an_absence_claim_that_names_its_search_is_silent(scripts_path):
    """Showing the work is the whole ask. The guard cannot judge whether the
    search was good, only whether one was named."""
    assert _warn(
        scripts_path,
        "No need covers vocabulary — grep across .claude/canvas/*.yml found none.",
    ) == ""


@pytest.mark.parametrize("cited", [
    "no source exists anywhere in landscape.yml",
    "checked all eleven statements: no entry covers it",
    "searched the canvas; nothing in it tracks this",
    "measured across 48 objects — no record exists",
])
def test_each_scope_form_suppresses(scripts_path, cited):
    assert _warn(scripts_path, cited) == ""


# ---------------------------------------------------------------- sad


def test_the_2026_08_04_sentence_warns(scripts_path):
    """Verbatim from the entry that was committed and pushed before being caught."""
    out = _warn(scripts_path, "So his signal has nowhere to go, and that is the finding.")
    assert "ABSENCE-CLAIM WARNING" in out
    assert "nowhere to go" in out
    assert "the write still proceeds" in out


@pytest.mark.parametrize("claim", [
    "nothing in the framework distinguishes them.",
    "That signal has never been routed into a need.",
    "No mechanism writes to that surface.",
    "The brownfield path does not exist.",
    "Those two contribute zero need sources.",
    "nobody audited the labels.",
])
def test_each_absence_shape_warns(scripts_path, claim):
    assert "ABSENCE-CLAIM WARNING" in _warn(scripts_path, claim)


def test_the_warning_explains_that_citing_is_not_enough(scripts_path):
    """The instance that motivated this guard CARRIED a citation and was still
    wrong, so a message that only says 'cite your search' would reproduce it."""
    out = _warn(scripts_path, "No check exists for that.")
    assert "scope" in out.lower()
    assert "checked all eleven statements" in out
    assert "ONE FILE" in out


# ---------------------------------------------------------------- edge


@pytest.mark.parametrize("ledger", [
    "No confidence gate moved.",
    "no skill or framework change applied.",
    "NO evidence entry drafted, NO confidence movement, task status unchanged.",
    "no asymmetry signals, no specific reason offered or asked.",
])
def test_ledger_prose_stays_silent(scripts_path, ledger):
    """CALIBRATION REGRESSION. These are records of what a session did, not
    claims about what exists — always true when written, no search behind them.
    The first draft warned on all four, which is how a guard trains its reader
    to skim. Real sentences from .claude/harness/decision-log.md and
    human-tasks.yml."""
    assert _warn(scripts_path, ledger) == ""


def test_a_path_outside_the_evidence_surfaces_is_silent(scripts_path):
    """Framework source and docs are full of legitimate absence prose."""
    assert _warn(scripts_path, "No check exists for that.",
                 path="/Users/x/proj/src/thing.py") == ""
    assert _warn(scripts_path, "No check exists for that.",
                 path="/Users/x/proj/README.md") == ""


def test_edit_payloads_are_read_from_new_string(scripts_path):
    """Edit carries new_string, not content. Reading only content would make the
    guard silent on the most common canvas-writing path."""
    assert "ABSENCE-CLAIM WARNING" in _warn(
        scripts_path, "No opportunity covers this.", tool="Edit")


def test_unknown_tools_contribute_nothing(scripts_path):
    assert _warn(scripts_path, "No check exists for that.", tool="Read") == ""


def test_several_claims_are_quoted_and_capped(scripts_path):
    out = _warn(scripts_path, "No entry covers alpha.\nNo entry covers beta.\n"
                              "No entry covers gamma.\nNo entry covers delta.")
    assert "alpha" in out and "beta" in out and "gamma" in out
    assert "and 1 more in this write" in out
    assert "delta" not in out


# ---------------------------------------------------------------- bad


def test_unparseable_payload_fails_open(scripts_path):
    r = _run(scripts_path, "{not json")
    assert r.returncode == 0
    assert r.stdout.strip() == ""


@pytest.mark.parametrize("payload", [
    "{}",
    json.dumps({"tool_name": "Write", "tool_input": None}),
    json.dumps({"tool_name": "Write", "tool_input": {"content": "No entry covers x."}}),
    json.dumps({"tool_name": "Write", "tool_input": {"file_path": CANVAS}}),
    json.dumps({"tool_name": "Write", "tool_input": {"file_path": CANVAS, "content": "   "}}),
])
def test_malformed_payloads_stay_silent(scripts_path, payload):
    r = _run(scripts_path, payload)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


# ---------------------------------------------------------------- in-process
# The tests above drive the hook as a subprocess, which is the right shape for
# the stdin/stdout contract and useless for coverage — coverage.py cannot
# instrument a child interpreter, so the per-file floor read this script at 0%
# and blocked the push. Same correction as shell_safety_guard, same day of the
# week later. These call the functions directly.


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import absence_claim_guard
    return absence_claim_guard


def test_findings_is_pure_and_returns_one_entry_per_claim(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings("Bentes drove the ship.") == []
    assert len(mod.findings("No entry covers it.")) == 1
    assert len(mod.findings("No entry covers it.\nnothing in the canvas tracks it.")) == 2


def test_findings_suppresses_when_a_search_is_named(scripts_path):
    mod = _import(scripts_path)
    assert mod.findings("No entry covers it — grep over .claude/canvas/*.yml.") == []


def test_findings_truncates_a_long_sentence_to_the_quote_budget(scripts_path):
    mod = _import(scripts_path)
    long_claim = "No entry covers " + ("x" * 400) + "."
    out = mod.findings(long_claim)
    assert len(out) == 1
    assert len(out[0]) == mod._QUOTE_CHARS
    assert out[0].endswith("...")


@pytest.mark.parametrize(("tool", "payload", "expected"), [
    ("Write", {"content": "abc"}, "abc"),
    ("Edit", {"new_string": "abc"}, "abc"),
    ("MultiEdit", {"edits": [{"new_string": "a"}, {"new_string": "b"}]}, "a\nb"),
    ("MultiEdit", {"edits": "not-a-list"}, ""),
    ("MultiEdit", {"edits": [{"new_string": 7}, {"nope": "x"}, "junk"]}, ""),
    ("Read", {"content": "abc"}, ""),
    ("Write", {"content": 7}, ""),
])
def test_payload_text_per_tool(scripts_path, tool, payload, expected):
    """MultiEdit shares the manifest matcher with Write and Edit, so reading only
    the first two would ship a guard silent on a third of its invocations."""
    mod = _import(scripts_path)
    assert mod._payload_text(tool, payload) == expected


def test_main_reads_stdin_and_emits_additional_context(scripts_path,
                                                       monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(_write("No entry covers it.")))
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "ABSENCE-CLAIM" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_off_the_evidence_surfaces(scripts_path, monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(
        _write("No entry covers it.", path="/p/src/a.py")))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


def test_main_fails_open_on_garbage(scripts_path, monkeypatch, capsys):
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""
