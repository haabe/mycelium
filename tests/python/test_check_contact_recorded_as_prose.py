"""The rule must bite on the real miss and stay quiet on the 47 lookalikes.

ht-076 recorded "lost nine touches to prose-only logging" and then lost a tenth
the same way, inside the entry documenting the rule. check_touch_log_order was
green throughout: it checks that the entries which EXIST are ordered, never that
the log is COMPLETE.

The danger in the fix is the naive version. On the dogfood corpus, "every dated
field needs a touch" is 2 real hits against 47 false positives — so the
contact-word filter IS the check, and these pin both directions.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_contact_recorded_as_prose

    return check_contact_recorded_as_prose


def test_the_real_miss_is_caught(scripts_path):
    """ht-076's eighth inbound: a field claiming a contact, no touch on that date."""
    mod = _import(scripts_path)
    tasks = [{
        "id": "ht-076",
        "eighth_inbound_2026_08_26_the_promise_is_discharged": "prose",
        "touch_log": [{"date": "2026-08-22", "direction": "inbound"}],
    }]
    assert mod.scan(tasks) == [("ht-076", "eighth_inbound_2026_08_26_the_promise_is_discharged",
                                "2026-08-26")]


def test_it_goes_quiet_once_the_touch_exists(scripts_path):
    mod = _import(scripts_path)
    tasks = [{
        "id": "ht-076",
        "eighth_inbound_2026_08_26_the_promise_is_discharged": "prose",
        "touch_log": [{"date": "2026-08-22"}, {"date": "2026-08-26"}],
    }]
    assert mod.scan(tasks) == []


def test_dated_fields_that_are_not_contacts_are_skipped(scripts_path):
    """47 of these in the live corpus. A naive rule would be 96% false positives."""
    mod = _import(scripts_path)
    tasks = [{
        "id": "ht-001",
        "FOUNDER_RULING_2026_08_24_NOT_TESTING_NAVI": "x",
        "pre_registered_read_2026_08_21": "x",
        "label_correction_2026_08_26": "x",
        "scored_at_horizon_2026_08_27": "x",
        "touch_log": [],
    }]
    assert mod.scan(tasks) == []


def test_underscore_and_hyphen_dates_both_parse(scripts_path):
    mod = _import(scripts_path)
    tasks = [{"id": "a", "reply_sent_2026-08-20": "x", "touch_log": []}]
    assert mod.scan(tasks) == [("a", "reply_sent_2026-08-20", "2026-08-20")]


def test_a_task_with_no_touch_log_still_reports(scripts_path):
    """An empty log is the worst case, not an exemption from the question."""
    mod = _import(scripts_path)
    assert mod.scan([{"id": "a", "first_inbound_2026_08_01": "x"}]) == [
        ("a", "first_inbound_2026_08_01", "2026-08-01")]


def test_a_missing_task_file_is_not_a_pass(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    assert mod.main(["--root", str(tmp_path)]) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_an_empty_task_list_is_not_a_pass(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "human-tasks.yml").write_text("pending_tasks: []\n")
    assert mod.main(["--root", str(tmp_path)]) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_an_unreadable_task_file_is_not_a_pass(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "human-tasks.yml").write_text("pending_tasks: [unclosed\n")
    assert mod.main(["--root", str(tmp_path)]) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_a_field_declaring_the_dates_unknown_is_not_a_contact_claim(scripts_path):
    """Fired on a field written to EXPLAIN its own findings, the day after shipping."""
    mod = _import(scripts_path)
    tasks = [{"id": "ht-090",
              "touch_dates_unknown_stated_2026_08_27": "the dates are not known",
              "touch_log": []}]
    assert mod.scan(tasks) == []


def test_corrected_and_retracted_are_still_caught(scripts_path):
    """Both live true positives are named that way. The exclusion must not reach them."""
    mod = _import(scripts_path)
    tasks = [{"id": "ht-090",
              "TOUCH_CORRECTED_2026_08_25_THE_ASK_WAS_MADE": "x",
              "RETRACTED_2026_08_24_THE_ASK_WAS_SENT": "x",
              "touch_log": []}]
    assert len(mod.scan(tasks)) == 2
