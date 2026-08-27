"""A waiver must cost something, and must never be silent.

Four dogfood instruments carry an empty `frozen_before` ON PURPOSE — an
agent-as-instrument that never self-logged has no freeze event to name, and
inventing one is the failure the contract exists to prevent. The check reported
that correct decision as a defect on every run, permanently, which is how the
next genuine INCOMPLETE arrives in a list already mostly noise.

The risk in fixing it is obvious: an exemption mechanism that is easy to claim
turns every INCOMPLETE into a waiver. These pin the cost.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_instrument_contract

    return check_instrument_contract


HEADER = """---
type: assumption-test
status: {status}
frozen_at: 2026-05-02
frozen_before:{fb}
{extra}score_by: 2026-12-01
---

body
"""

GOOD = ("frozen_before_absent_reason: >-\n"
        "  LEFT EMPTY BY FOUNDER RULING 2026-08-20. This file states no freeze event and\n"
        "  inventing a plausible one is the failure the contract exists to prevent.\n")


def _fm(mod, extra="", fb="", status="scored"):
    return mod._frontmatter(HEADER.format(extra=extra, fb=fb, status=status))


def test_an_empty_field_with_no_reason_is_still_incomplete(scripts_path):
    mod = _import(scripts_path)
    missing, waived = mod._required_field_state(_fm(mod))
    assert "frozen_before" in missing
    assert waived == []


def test_a_substantive_reason_waives_it(scripts_path):
    mod = _import(scripts_path)
    missing, waived = mod._required_field_state(_fm(mod, extra=GOOD))
    assert "frozen_before" not in missing
    assert waived and waived[0][0] == "frozen_before"
    assert "FOUNDER RULING" in waived[0][1]


def test_a_token_reason_does_not_buy_an_exemption(scripts_path):
    """`n/a` must not be cheaper than writing the field."""
    mod = _import(scripts_path)
    for token in ("n/a", "x", "  ", "TODO"):
        missing, waived = mod._required_field_state(
            _fm(mod, extra=f"frozen_before_absent_reason: {token}\n"))
        assert "frozen_before" in missing, token
        assert waived == [], token


def test_a_filled_field_is_neither_missing_nor_waived(scripts_path):
    mod = _import(scripts_path)
    missing, waived = mod._required_field_state(_fm(mod, fb=" 2026-05-01"))
    assert "frozen_before" not in missing
    assert waived == []


def test_a_waiver_does_not_move_the_exit_code_but_is_printed(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    d = tmp_path / ".claude" / "evals" / "assumption-tests"
    d.mkdir(parents=True)
    (d / "2026-05-02-a.md").write_text(HEADER.format(extra=GOOD, fb="", status="scored"))
    res = mod.analyse(tmp_path, __import__("datetime").date(2026, 8, 27))
    assert res["waived"] and not res["incomplete"]


def test_folded_blocks_parse_as_their_content_not_as_the_indicator(scripts_path):
    """They parsed as the literal '>-' — a long field reading as two characters."""
    mod = _import(scripts_path)
    fm = _fm(mod, extra=GOOD)
    val = fm["frozen_before_absent_reason"]
    assert val.startswith("LEFT EMPTY")
    assert ">-" not in val
    assert "inventing a plausible one" in val, "continuation lines must be folded in"


def test_a_folded_block_does_not_swallow_the_next_key(scripts_path):
    mod = _import(scripts_path)
    fm = _fm(mod, extra=GOOD)
    assert fm["score_by"] == "2026-12-01"
    assert fm["type"] == "assumption-test"
