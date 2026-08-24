"""Coverage for read_before_research_guard.py — the read-before-RESEARCH gap.

THE DEFECT (i-productified dogfood, 2026-08-24, reproduced in this repo). Mycelium
had a read-before-WRITE preflight on 24 skills and NO read-before-RESEARCH rule
anywhere in skills/, engine/, harness/, scripts/, hooks/ or the consumer CLAUDE.md.

Two failures in one session, the second AFTER the prose lesson was written:
  1. ~6 searches and 4 fetches rebuilt an ownership structure the canvas already held
     in a sharper form.
  2. Minutes later the agent recommended a company as "a genuine find" that the canvas
     recorded the founder rejecting on ethical grounds.

The second is why the tier is WARN and the framing is CONSTRAINT LOSS rather than
token efficiency: what was lost was a decision already taken, not a few searches.
"""
import json
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import read_before_research_guard

    return read_before_research_guard


def _canvas(project, name, body):
    p = project / ".claude" / "canvas" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


def _run(mod, payload, capsys):
    sys.stdin = None  # main() reads json from stdin; call the pieces directly instead
    query = mod._query_from(payload)
    terms = mod.candidates(query)
    hits = mod.search_canvas(__import__("pathlib").Path(payload["cwd"]), terms)
    return terms, hits


# --- entity extraction ------------------------------------------------------

def test_capitalised_tokens_are_candidates(scripts_path):
    mod = _import(scripts_path)
    assert "Sporsem" in mod.candidates("Tor Sporsem SINTEF requirements engineering")


def test_quoted_phrases_are_candidates(scripts_path):
    mod = _import(scripts_path)
    assert any("green energy" in c.lower()
               for c in mod.candidates('"green energy holding" ownership'))


def test_question_words_are_not_candidates(scripts_path):
    """Over-filtering reintroduces the gap, so the stoplist is short — but a query
    opening with 'What' must not fire on the word 'What'."""
    mod = _import(scripts_path)
    assert "What" not in mod.candidates("What is the ownership structure")


def test_short_and_lowercase_tokens_are_ignored(scripts_path):
    mod = _import(scripts_path)
    assert mod.candidates("the ownership of a small firm") == []


# --- the two failures this shipped for --------------------------------------

def test_entity_already_in_canvas_produces_a_hit(scripts_path, tmp_path):
    """Instance 1: the canvas already held it, in a sharper form."""
    mod = _import(scripts_path)
    _canvas(tmp_path, "human-tasks.yml",
            "tasks:\n  - id: ht-001\n    note: Sporsem sent a connection request\n")
    terms = mod.candidates("Tor Sporsem SINTEF research")
    hits = mod.search_canvas(tmp_path, terms)
    assert hits and hits[0][0] == "Sporsem"
    assert hits[0][1] == "human-tasks.yml"


def test_the_severity_case_a_recorded_judgement_surfaces(scripts_path, tmp_path):
    """Instance 2, and the reason this is not a token-efficiency check.

    The canvas records a POSITION, not a fact. If this ever stops surfacing, the
    guard has lost the only failure that actually cost something.
    """
    mod = _import(scripts_path)
    _canvas(tmp_path, "purpose.yml",
            "why: x\nnotes: Nordkraft rebrand is greenwashing, ruled out on ethics\n")
    hits = mod.search_canvas(tmp_path, mod.candidates("Nordkraft sustainability report"))
    assert hits
    assert "greenwashing" in hits[0][3]


def test_no_canvas_means_silence(scripts_path, tmp_path):
    """Fail open. A project without a canvas must never be nagged."""
    mod = _import(scripts_path)
    assert mod.search_canvas(tmp_path, ["Sporsem"]) == []


def test_unmatched_entity_is_silent(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _canvas(tmp_path, "purpose.yml", "why: something unrelated\n")
    assert mod.search_canvas(tmp_path, mod.candidates("Volkswagen emissions")) == []


def test_hits_are_capped(scripts_path, tmp_path):
    """A warning that dumps the canvas is a warning nobody reads."""
    mod = _import(scripts_path)
    _canvas(tmp_path, "landscape.yml", "\n".join(f"  - note: Acme item {i}" for i in range(40)))
    assert len(mod.search_canvas(tmp_path, ["Acme"])) <= 3


# --- contract ---------------------------------------------------------------

def test_query_is_read_from_several_tool_shapes(scripts_path):
    mod = _import(scripts_path)
    assert mod._query_from({"tool_input": {"query": "a"}}) == "a"
    assert mod._query_from({"tool_input": {"url": "b"}}) == "b"
    assert mod._query_from({"tool_input": {}}) == ""


def test_message_carries_the_severity_framing(scripts_path):
    """The 'not token efficiency' framing is load-bearing and must ship in the
    warning itself, not only in the changelog."""
    mod = _import(scripts_path)
    msg = mod.build_message([("Acme", "purpose.yml", 3, "ruled out on ethics")])
    assert "RECORD OF JUDGEMENTS" in msg.upper()
    assert "never blocks" in msg


def test_malformed_stdin_fails_open(scripts_path, monkeypatch, capsys):
    """A broken payload must cost the user nothing."""
    import io
    mod = _import(scripts_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


def test_firing_is_logged_for_later_tier_calibration(scripts_path, tmp_path, monkeypatch, capsys):
    """The log is the instrument that decides whether this guard survives.

    sol-048a already commits this project to retiring a guard whose action rate
    stays near zero. Without the log there is no way to run that test.
    """
    import io
    mod = _import(scripts_path)
    _canvas(tmp_path, "purpose.yml", "notes: Nordkraft ruled out on ethics\n")
    payload = {"tool_name": "WebSearch", "cwd": str(tmp_path),
               "tool_input": {"query": "Nordkraft annual report"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert mod.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert "additionalContext" in out["hookSpecificOutput"]
    logged = (tmp_path / ".claude" / "state" / "read-before-research-log.jsonl").read_text()
    rec = json.loads(logged.strip().splitlines()[0])
    assert rec["hook"] == "read-before-research-guard"
    assert rec["tool"] == "WebSearch"
