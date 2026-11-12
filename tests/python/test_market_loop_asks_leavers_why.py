"""The L5 -> L2 loop asks the people who left why, before it hands back to discovery (2026-10-05).

WHAT WAS WRONG. `/mycelium:launch-tier`'s After Launch loop captured retention, churn, refund rate
and support tickets: counts of who left. No step asked those people why. The only place the
question appeared was one row of harness/cognitive-biases.md (survivorship bias), met only in a
bias check, so an L2 re-targeted on a guess about why the number moved. The dogfood L5 had to build
the instrument by hand (ask at 3, 7 and 14 days, one question each, stop at a clear no).

WHAT THIS PINS. The step exists inside the After Launch loop, before the hand-off back to the L2,
asks in the person's own words rather than by form, says the human sends, and routes each reason to
an opportunity. The bias-check row it cites is still where it says it is.
"""

from __future__ import annotations

import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SKILL = PLUGIN / "skills" / "launch-tier" / "SKILL.md"


def _loop() -> str:
    text = SKILL.read_text(encoding="utf-8")
    start = text.index("## After Launch: The L5 -> L2 Feedback Loop")
    return text[start:text.index("## Cycle History Recording", start)]


def test_the_loop_asks_the_people_who_left_why():
    assert re.search(r"asks? (the people|those) who (left|stopped)", _loop())


def test_the_ask_comes_before_the_hand_off_to_discovery():
    loop = _loop()
    assert loop.index("1b. **Name who left") < loop.index("4. **Feed back into discovery**")


def test_the_step_asks_in_their_words_has_a_rhythm_and_a_sender():
    step = _loop().split("1b. ", 1)[1].split("\n2. ", 1)[0]
    for phrase in ("in their own words", "stop at a clear no", "harness/delegation-authority.md",
                   "Route each reason to the opportunity"):
        assert phrase in step, f"the leavers step no longer says {phrase!r}"


def test_the_cited_bias_row_still_exists():
    biases = (PLUGIN / "harness" / "cognitive-biases.md").read_text(encoding="utf-8")
    assert "Ask who left and why." in biases
