#!/usr/bin/env python3
"""Find contacts written as PROSE that never became a touch.

WHY THIS EXISTS. `ht-076` in the dogfood repo carries the line *"lost nine touches
to prose-only logging"* — and then lost a tenth, the same way, inside the entry that
documents the rule. An eighth inbound arrived 2026-08-26, was written up as a field
called `eighth_inbound_2026_08_26_...`, and never entered `touch_log`. The same
defect sits on `ht-090` twice more, undetected since 2026-08-24.

THE COST IS NOT TIDINESS. `touch_log` is what every downstream reader consumes.
`check_reply_owed` read ht-076's last inbound as five days old when it was one day
old, because it reads the log and the log did not know. A contact recorded only in
prose is invisible to every check, to the attribution registry, and to the exclusion
duty that later sweeps owe to already-touched populations.

WHY NOTHING CAUGHT IT. `check_touch_log_order` verifies that entries are in ascending
date order — it is a check on the entries that EXIST. Nothing asked whether the log
was COMPLETE. Ordering and completeness are different questions and only one was
being asked.

THE RULE, AND WHY IT IS NARROW ON PURPOSE. A field NAME that carries both a date and
a contact word (`inbound`, `reply`, `sent`, `touch`, ...) is claiming a contact
happened on that date. If no touch_log entry shares the date, the claim exists in
prose only.

MEASURED BEFORE SHIPPING, on the 26-task dogfood corpus:
  - 2 real hits, both the known-unfixed ht-090 pair.
  - 47 dated fields correctly SKIPPED for having no contact word — `FOUNDER_RULING_
    2026_08_24`, `pre_registered_read_2026_08_21`, `label_correction_2026_08_26` and
    friends. **A naive "dated field must have a touch" rule would be 96% false
    positives**, which is why the contact-word filter is the check rather than a
    refinement of it.
  - Negative control: against ht-076's state before the backfill, the rule fires on
    exactly the field that was missed, and goes silent after it.

KNOWN FALSE-POSITIVE CLASS, classified rather than filtered blind. A field written
ABOUT the log's own gaps carries a contact word and a date, and that date is when the
STATEMENT was made -- `touch_dates_unknown_stated_2026_08_27` is the live example, and it
appeared the day after this shipped. Fields declaring the dates unknown are skipped. The
near neighbours `corrected` and `retracted` are deliberately NOT skipped: both live true
positives are named that way and describe real contacts.

REPORT-ONLY. A date in a field name is a strong hint, not a contract, and some
contacts legitimately have no known event date — ht-090's deflected ask is real and
undated, and inventing a date to satisfy a gate would be worse than the gap.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - reported, never silently skipped
    yaml = None

TASKS = pathlib.Path(".claude/canvas/human-tasks.yml")
DATE_IN_NAME = re.compile(r"(20\d\d)[_-](\d\d)[_-](\d\d)")
# Words that make a field name a CLAIM ABOUT A CONTACT rather than about an internal
# event. Kept deliberately short: every addition widens the check toward the naive
# rule the docstring measures at 96% false positives.
CONTACT_WORD = re.compile(r"inbound|outbound|repl(y|ies)|sent|touch|dm\b|message", re.IGNORECASE)
# A FIELD THAT SAYS THE DATES ARE UNKNOWN IS NOT CLAIMING A DATED CONTACT.
# Found the day after shipping, by this check firing on a field written to explain its
# own two findings: `touch_dates_unknown_stated_2026_08_27` carries a contact word and a
# date, and that date is when the STATEMENT was made. Narrow on purpose -- `corrected`
# and `retracted` are deliberately NOT here, because both live true positives are named
# `TOUCH_CORRECTED_...` and `RETRACTED_...` and describe real contacts.
NOT_A_CONTACT_CLAIM = re.compile(r"unknown", re.IGNORECASE)


def scan(tasks: list) -> list[tuple[str, str, str]]:
    """(task_id, field_name, iso_date) for contact-claiming fields with no touch."""
    out = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        logged = {str(e.get("date")) for e in (task.get("touch_log") or [])
                  if isinstance(e, dict)}
        for field in task:
            m = DATE_IN_NAME.search(field)
            if not m or not CONTACT_WORD.search(field):
                continue
            if NOT_A_CONTACT_CLAIM.search(field):
                continue
            iso = "-".join(m.groups())
            if iso not in logged:
                out.append((str(task.get("id", "(no id)")), field, iso))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)

    if yaml is None:
        print("UNKNOWN: PyYAML unavailable, so nothing was checked.", file=sys.stderr)
        return 2

    path = pathlib.Path(args.root) / TASKS
    if not path.is_file():
        # Zero inputs is not a pass.
        print(f"UNKNOWN: no {TASKS} under {args.root} — nothing was checked.",
              file=sys.stderr)
        return 2
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        print(f"UNKNOWN: could not read {path} ({exc}). Nothing was checked.",
              file=sys.stderr)
        return 2

    tasks = data.get("pending_tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list) or not tasks:
        print(f"UNKNOWN: {TASKS} holds no pending_tasks — nothing was checked.",
              file=sys.stderr)
        return 2

    findings = scan(tasks)
    print(f"prose-only contacts: scanned {len(tasks)} task(s), {len(findings)} finding(s)")
    if not findings:
        print("  Every field naming a dated contact has a touch_log entry on that date.")
        return 0

    print("\nRECORDED AS PROSE, NOT AS A TOUCH — the field name claims a contact on a date "
          "the\ntouch_log does not have. touch_log is what the other checks read: a contact "
          "only in\nprose is invisible to reply-owed, to the attribution registry, and to the "
          "exclusion\nduty later sweeps owe an already-touched population.")
    for task_id, field, iso in findings:
        print(f"  {task_id:<8} {iso}  {field}")
    print("\nDO NOT INVENT A DATE TO CLEAR THIS. Some contacts genuinely have no known event "
          "date;\nan entry dated by when it was REPORTED asserts an event date nobody has. "
          "Either log\nthe touch with its real date, or say in the task that the date is unknown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
