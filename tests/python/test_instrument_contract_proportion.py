"""A test is sized to the decision it informs, and the founder can override that with a reason.

E2E runs 53-55: a recipe page for five opted-in testers pre-registered a re-test needing twelve blind
recipe lines and a government nutrition dataset, and stalled three sessions on inputs the world could
not supply. Founder, 2026-09-26: size tests to the decision, "but have an override flag that lets a
founder run costly tests if reasoned well" (v0.264.0).
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_instrument_contract

    return check_instrument_contract


def _run(mod, extra, frozen="2026-10-01"):
    text = ("---\ntype: assumption-test\nstatus: live\nfrozen_at: " + frozen +
            "\nfrozen_before: the first tester opens the page\nscore_by: 2026-12-01\n"
            "does_not_reproduce: nothing outside the five testers\n" + extra + "---\nbody\n")
    fm = mod._frontmatter(text)
    res = {"oversized": [], "costly_override": [], "bad_proportion": []}
    mod._proportion("t.md", fm, res)
    return fm, res


REASON = ("costly_test_reason: the leavening rule decides whether a public page ruins bakes, and a "
          "blind sample is the only way to know\n")


def test_a_test_no_heavier_than_its_decision_passes(scripts_path):
    mod = _import(scripts_path)
    for cls, weight in (("light", "light"), ("standard", "light"), ("heavy", "heavy")):
        _, res = _run(mod, f"decision_class: {cls}\ntest_weight: {weight}\n")
        assert res == {"oversized": [], "costly_override": [], "bad_proportion": []}


def test_a_heavy_test_for_a_light_decision_is_oversized(scripts_path):
    mod = _import(scripts_path)
    _, res = _run(mod, "decision_class: light\ntest_weight: heavy\n")
    assert res["oversized"] == [("t.md", "heavy test for a light decision")]


def test_the_founder_can_override_with_a_written_reason(scripts_path):
    mod = _import(scripts_path)
    _, res = _run(mod, "decision_class: light\ntest_weight: heavy\n" + REASON +
                  "costly_test_by: founder\n")
    assert res["oversized"] == [] and len(res["costly_override"]) == 1
    assert res["costly_override"][0][2] == "founder"


def test_the_override_needs_a_real_reason_and_a_human(scripts_path):
    mod = _import(scripts_path)
    for extra in ("costly_test_reason: because\ncostly_test_by: founder\n",
                  REASON + "costly_test_by: agent\n", REASON):
        _, res = _run(mod, "decision_class: light\ntest_weight: heavy\n" + extra)
        assert res["oversized"], extra


def test_an_unknown_size_is_reported(scripts_path):
    mod = _import(scripts_path)
    _, res = _run(mod, "decision_class: tiny\ntest_weight: light\n")
    assert res["bad_proportion"] == [("t.md", "decision_class: 'tiny'")]


def test_the_sizes_are_required_from_2026_09_27_only(scripts_path):
    mod = _import(scripts_path)
    fm, _ = _run(mod, "")
    missing, _ = mod._required_field_state(fm)
    assert "decision_class" in missing and "test_weight" in missing
    fm, _ = _run(mod, "", frozen="2026-09-20")
    missing, _ = mod._required_field_state(fm)
    assert "decision_class" not in missing, "a corpus written before the rule is not failed by it"
