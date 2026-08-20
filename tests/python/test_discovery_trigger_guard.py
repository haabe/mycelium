"""Coverage proof for discovery_trigger_guard.py.

THE GAP IT CLOSES. Every route into discovery in this framework is INVOKED --
/assumption-test, /user-interview, /handoff all wait to be called. The founder's
report (dogfood 2026-08-20, opp-051 sol-051h) is that the moment needing
discovery is exactly the moment nobody recognises it: "the user might not be
aware that this requires discovery in the post." A skill cannot fire on a case
its author did not notice.

CALIBRATION IS THE CONTRACT HERE, not a detail, because the named way this hook
dies is over-triggering (opp-051 sol-051h risk (a), which inherits sol-048a's
rule: a guard whose action rate stays near zero is narrowed or retired). So the
suppressors get as many tests as the triggers. A guard that fires on grounded
work, on the author's own experience, or on an honest question gets disabled by
its user within a day, and a disabled guard has an action rate of zero.

Scenario-per-guardpost:
  sad   — "users want X"                              -> advise
  sad   — "people won't bother with it"               -> advise
  sad   — "they'd pay for that"                       -> advise
  sad   — "nobody needs another one of these"         -> advise
  happy — grounded in reported speech ("X said ...")  -> silence
  happy — already typed ("I assume users want")       -> silence
  happy — an honest question ("what do users want?")  -> silence
  happy — the author about himself ("I keep...")      -> silence
  happy — cites an evidence id (ht-064)               -> silence
  happy — ordinary build request                      -> silence
  edge  — "they" without a dispositional modal        -> silence (loose corefer)
  edge  — several claims in one prompt                -> all quoted, capped at 2
  edge  — a fire writes one JSONL row (the instrument)
  bad   — unparseable payload                         -> silence, exit 0
  bad   — payload with no prompt key                  -> silence, exit 0
  bad   — non-string prompt                           -> silence, exit 0
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "mycelium" / "scripts" / "discovery_trigger_guard.py"
)


def run(payload, cwd=None):
    """Run the guard over a payload. Returns (returncode, parsed_or_None)."""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=raw, capture_output=True, text=True, check=False,
        cwd=str(cwd) if cwd else None,
        env={"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(cwd)} if cwd else None,
    )
    out = proc.stdout.strip()
    return proc.returncode, (json.loads(out) if out else None)


def advises(prompt, cwd=None):
    code, parsed = run({"prompt": prompt}, cwd=cwd)
    assert code == 0, "the guard must never fail a prompt"
    return parsed is not None


def context(prompt):
    _, parsed = run({"prompt": prompt})
    return parsed["hookSpecificOutput"]["additionalContext"]


# --- sad paths: the claim shapes this exists to catch ------------------------

@pytest.mark.parametrize("prompt", [
    "Let's shorten onboarding, users want to get started faster.",
    "People won't bother reading a long setup guide.",
    "Skip the tour. They'd pay for the pro tier without it anyway.",
    "Nobody needs another one of these unless it is fast.",
    "Our customers prefer a single dashboard over separate views.",
    "Developers hate configuring things by hand.",
])
def test_unhedged_claims_about_people_advise(prompt):
    assert advises(prompt), f"should have advised on: {prompt}"


def test_message_offers_typing_before_testing():
    """Risk (b): the first response must never be 'run a study'."""
    msg = context("users want faster onboarding")
    assert "TYPE IT" in msg
    assert msg.index("TYPE IT") < msg.index("TEST IT"), "typing must be offered first"
    assert "internal_stakeholder" in msg, "own-domain-knowledge must stay legitimate"
    assert "FLAG THE GAP" in msg, "must degrade when the author has no access"


# --- happy paths: calibration. these must stay silent ------------------------

@pytest.mark.parametrize("prompt", [
    # grounded in something someone actually said or did
    "The support lead said users want faster onboarding, so let's shorten it.",
    "In the interview she told me people won't bother with the setup guide.",
    "According to the survey, customers prefer one dashboard.",
    "ht-064 recorded that developers hate hand-configuring this.",
    # already typed honestly
    "My assumption is that users want faster onboarding.",
    "I think people would pay for this, but it is a guess.",
    "Unvalidated: nobody needs another one of these.",
    # a question is the right instinct, not a lapse
    "What do users want from the onboarding flow?",
    "Do people actually need the tour?",
    # the author about his own experience -- internal_stakeholder evidence
    "I want to shorten onboarding because I keep losing my place.",
    "I need this to be faster.",
    # ordinary build work
    "Refactor the parser and add a test for the empty-input case.",
    "Fix the failing CI job on main.",
])
def test_grounded_typed_interrogative_and_first_person_stay_silent(prompt):
    assert not advises(prompt), f"should have stayed silent on: {prompt}"


def test_loose_pronoun_alone_does_not_fire():
    """'they' corefers to anything; only a dispositional modal makes it a claim."""
    assert not advises("The tests are flaky. They fail on CI but not locally.")


# --- edges -------------------------------------------------------------------

def test_multiple_claims_are_quoted_and_capped():
    msg = context(
        "Users want faster onboarding. People won't bother with the guide. "
        "Developers hate hand-configuring this. Customers prefer one dashboard."
    )
    assert "and 2 more in this prompt" in msg
    assert msg.count("    > ") == 2


def test_fire_appends_one_row_to_the_instrument(tmp_path):
    """The action-rate log ships with the trigger, per sol-048a's rule."""
    assert advises("Users want faster onboarding.", cwd=tmp_path)
    log = tmp_path / ".claude" / "state" / "discovery-trigger-log.jsonl"
    assert log.exists(), "a fire must be recordable or the action rate is unmeasurable"
    rows = [json.loads(x) for x in log.read_text().splitlines() if x.strip()]
    assert len(rows) == 1
    assert rows[0]["hook"] == "discovery-trigger-guard"
    assert rows[0]["fires"] == 1
    assert "at" in rows[0]


def test_silence_writes_no_row(tmp_path):
    assert not advises("Fix the failing CI job on main.", cwd=tmp_path)
    log = tmp_path / ".claude" / "state" / "discovery-trigger-log.jsonl"
    assert not log.exists(), "silence must not be logged as a fire"


def test_log_records_what_fired_not_the_prompt(tmp_path):
    prompt_with_credential = "Users want faster onboarding. My API key is sk-do-not-log-me."
    assert advises(prompt_with_credential, cwd=tmp_path)
    body = (tmp_path / ".claude" / "state" / "discovery-trigger-log.jsonl").read_text()
    assert "sk-do-not-log-me" not in body, "the log is a rate counter, not a transcript"


# --- bad paths: fail open ----------------------------------------------------

@pytest.mark.parametrize("payload", [
    "not json at all",
    "",
    json.dumps({}),
    json.dumps({"prompt": None}),
    json.dumps({"prompt": 42}),
    json.dumps({"something_else": "users want things"}),
])
def test_malformed_payloads_fail_open(payload):
    code, parsed = run(payload)
    assert code == 0
    assert parsed is None


# --- in-process unit coverage ------------------------------------------------
# The subprocess tests above prove the SHIPPED contract (a hook is invoked as a
# process, so that is the real interface). These import the module so the
# per-file coverage floor can see it, and so the detector can be exercised
# without paying process startup on every case.

def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import discovery_trigger_guard

    return discovery_trigger_guard


def test_claim_sentences_isolates_the_detector(scripts_path):
    mod = _import(scripts_path)
    assert mod._claim_sentences("Users want faster onboarding.") == [
        "Users want faster onboarding."
    ]
    assert mod._claim_sentences("The support lead said users want faster onboarding.") == []
    assert mod._claim_sentences("") == []
    assert mod._claim_sentences("Short.") == []


def test_detector_splits_on_sentences_not_prompts(scripts_path):
    mod = _import(scripts_path)
    hits = mod._claim_sentences(
        "Fix the CI job. Users want faster onboarding. I want a nap."
    )
    assert hits == ["Users want faster onboarding."], (
        "only the claim sentence is quoted — surrounding work and first-person "
        "statements must not be dragged in"
    )


def test_long_claim_is_truncated_for_quoting(scripts_path):
    mod = _import(scripts_path)
    long_claim = "Users want " + ("a much faster onboarding flow " * 12) + "please."
    hit = mod._claim_sentences(long_claim)[0]
    assert len(hit) <= mod._QUOTE_CHARS
    assert hit.endswith("…")


def test_main_advises_in_process(scripts_path, tmp_path, monkeypatch, capsys):
    """main() over stdin — the same path the hook drives, measured in-process."""
    mod = _import(scripts_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(
        "sys.stdin", io.StringIO(json.dumps({"prompt": "Users want faster onboarding."}))
    )
    assert mod.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "TYPE IT" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_in_process(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "Fix the CI job."})))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


def test_main_fails_open_on_garbage_in_process(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert mod.main() == 0
    assert capsys.readouterr().out == ""


def test_log_is_silent_when_the_path_is_unwritable(scripts_path, tmp_path, monkeypatch):
    """An instrument that breaks a session is worse than one with a gap."""
    mod = _import(scripts_path)
    blocker = tmp_path / "blocked"
    blocker.write_text("i am a file, not a directory")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(blocker))
    mod._log(["Users want faster onboarding."])  # must not raise


def test_log_appends_rather_than_truncates(scripts_path, tmp_path, monkeypatch):
    mod = _import(scripts_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    mod._log(["Users want a."])
    mod._log(["People want b.", "They would pay."])
    rows = [
        json.loads(x)
        for x in (tmp_path / ".claude" / "state" / "discovery-trigger-log.jsonl")
        .read_text().splitlines() if x.strip()
    ]
    assert [r["fires"] for r in rows] == [1, 2], "each fire is one row, appended"
