"""The Noise Check in /mycelium:ice-score gives no number it has no source for (0.320.0).

Until 0.320.0 it read "If scores diverge by >1 point on any dimension", in two places. The number
carried no citation and was written when each dimension was a 1-10 rating. Since 0.319.0 Confidence
is a sum of Gilad's Confidence Meter weights, where most values are under 1: two scorings of 0.16
and 0.96 are less than "1 point" apart and one total is six times the other. No sourced number
replaces it, so the skill says that "too close to call" is a judgement stated with its reason.

The test reads the shipped skill text, without the history note that quotes the old wording.
"""
import re
from pathlib import Path

SKILL = (Path(__file__).resolve().parents[2]
         / "plugins" / "mycelium" / "skills" / "ice-score" / "SKILL.md")


def _noise_check() -> str:
    text = SKILL.read_text(encoding="utf-8")
    section = text[text.index("### Noise Check (Kahneman, Sibony & Sunstein, 2021)"):]
    return re.sub(r"\*\((?:Changed|Until) .*?\)\*", "", section, flags=re.DOTALL)


def test_the_noise_check_keeps_its_attribution_and_its_procedure():
    live = _noise_check()
    for part in ("**Detection**:", "**Mitigation**:", "**Noise audit procedure**:"):
        assert part in live, part
    assert "re-score after a 24h break" in live


def test_the_noise_check_states_no_point_threshold():
    live = _noise_check()
    assert ">1 point" not in live and "> 1 point" not in live
    assert not re.search(r"diverge by\s*>?\s*\d", live), "no numeric divergence cutoff"
    assert "No number says how far apart two scorings must be" in live
    assert '**"Too close to call" is a judgement, stated with its reason.**' in live


def test_the_noise_check_is_written_for_the_current_scale():
    live = _noise_check()
    assert "Each factor is 0-10 and the total is their product" in live
    assert "summed from the Confidence Meter" in live


def test_the_output_rule_says_within_noise_has_no_number():
    text = SKILL.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines()
                if ln.startswith("If the top two scores are within noise of each other"))
    assert 'There is no number for "within noise"' in line
