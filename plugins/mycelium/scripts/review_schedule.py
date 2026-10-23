#!/usr/bin/env python3
"""review_schedule.py — which scheduled reviews are past their cadence, read from their output.

WHY THIS EXISTS (dogfood, 2026-10-23, the founder: "a lot of the recurring evaluations ... go on
unpassed. Nothing automatically picks up that they weren't run in time"). engine/feedback-loops.md
set a schedule in prose and listed "SessionStart: remind about overdue strategic reviews" as needed
work; two rows became checks (bvssh, delivery metrics) and the rest lapsed unseen. Measured from
each review's own output and git: theory-fidelity went 111 days on a quarterly cadence, and
wardley-map 63 and 41 days on a monthly one. The two reviews that had a check stayed within two
days of theirs.

WHERE A LAST RUN IS READ FROM. engine/review-schedule.yml names it per review. A review that writes
dated files anyway is read from them (the newest YYYY-MM-DD in a matching file name), so nothing new
has to be remembered. A review that writes only the decision log ends with `--record <id>`, which
appends one line to .claude/harness/review-runs.jsonl. The decision log's headings are free text,
and reading them was measured to undercount: the first measurement behind this script called two
reviews 114 and 143 days late, and their own files said 12 and 64.

VERBS
  --check   one advisory line for session start, "SCHEDULED REVIEWS DUE — N review(s) past their
            cadence: ..." or "OK: ...". Exit 0 either way; it is an advisory, never a gate. A
            schedule or record that cannot be read is said out loud ("UNREADABLE ... did NOT run"),
            never counted as nothing due.
  --list    the whole schedule with each review's last run and state, for /mycelium:feedback-review.
  --record  append a run of <id> (today unless --date). An id the schedule does not name exits 1.

NEVER RUN. A review with no run on record is due once the project's oldest diamond is older than its
cadence, or, for a corrections cadence, once that many corrections exist. A project with no diamonds
has nothing due.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _state_dir

SCHEDULE = Path(__file__).resolve().parent.parent / "engine" / "review-schedule.yml"
RUNS_REL = ".claude/harness/review-runs.jsonl"
CORRECTIONS_REL = ".claude/memory/corrections.md"
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_CORRECTION_HEAD = re.compile(r"^## (\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _date(text) -> _dt.date | None:
    m = _DATE.search(str(text or ""))
    if not m:
        return None
    try:
        return _dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def load_schedule(path: Path) -> tuple[list[dict], str | None]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [], f"{path}: {exc}"
    reviews = doc.get("reviews") if isinstance(doc, dict) else None
    if not isinstance(reviews, list) or not reviews:
        return [], f"{path}: no `reviews` list"
    return [r for r in reviews if isinstance(r, dict) and r.get("id")], None


def stamps(root: Path) -> tuple[dict[str, _dt.date], str | None]:
    """Newest recorded run per review id; an unreadable line is an error, not a skip."""
    path = root / RUNS_REL
    out: dict[str, _dt.date] = {}
    if not path.is_file():
        return out, None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return out, f"{path} line {n} is not JSON"
        rid, when = row.get("review"), _date(row.get("date"))
        if not (rid and when):
            return out, f"{path} line {n} has no review id or no valid date"
        if rid not in out or when > out[rid]:
            out[rid] = when
    return out, None


def _newest_file_date(root: Path, pattern: str) -> _dt.date | None:
    dates = [d for p in root.glob(pattern) if (d := _date(p.name))]
    return max(dates) if dates else None


def last_run(root: Path, review: dict, stamped: dict[str, _dt.date]) -> _dt.date | None:
    src = review.get("last_run") or {}
    found = []
    if src.get("files"):
        found.append(_newest_file_date(root, src["files"]))
    if src.get("stamp"):
        found.append(stamped.get(review["id"]))
    found = [d for d in found if d]
    return max(found) if found else None


def corrections_since(root: Path, since: _dt.date | None) -> int:
    path = root / CORRECTIONS_REL
    if not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    dates = [d for h in _CORRECTION_HEAD.findall(text) if (d := _date(h))]
    return sum(1 for d in dates if since is None or d > since)


def oldest_diamond(root: Path) -> tuple[_dt.date | None, str | None]:
    """(oldest diamond's birth date, error). No diamonds file is a project with nothing due; a
    file that cannot be read is an error, never read as "no diamonds", which would say nothing
    is due when the check could not look."""
    path = root / ".claude/diamonds/active.yml"
    if not path.is_file():
        return None, None
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return None, f"{path}: {exc}"
    if not isinstance(doc, dict):
        return None, f"{path}: not a mapping"
    entries = [d for key in ("active_diamonds", "completed_diamonds")
               for d in (doc.get(key) or []) if isinstance(d, dict)]
    born = [w for d in entries
            if (w := _date(d.get("created_at") or d.get("opened_at") or d.get("created")))]
    return (min(born) if born else None), None


def _cadence_text(cad: dict) -> str:
    if cad.get("corrections"):
        return f"every {cad['corrections']} corrections"
    return f"every {cad.get('days')} days"


def _judge(root: Path, review: dict, last: _dt.date | None, today: _dt.date,
           born: _dt.date | None) -> tuple[str, str]:
    """(state, detail) for one review that applies and is not checked elsewhere."""
    cad = review.get("cadence") or {}
    if cad.get("corrections"):
        n = corrections_since(root, last)
        since = f"since {last}" if last else "with no run on record"
        if n >= int(cad["corrections"]):
            return "due", f"{n} correction(s) logged {since}"
        return "ok", f"{n} correction(s) logged {since}"
    days = int(cad.get("days") or 0)
    if last:
        age = (today - last).days
        return ("due" if age > days else "ok"), f"last run {last}, {age} days ago"
    if born and (today - born).days > days:
        return "due", f"no run on record; the oldest diamond is {(today - born).days} days old"
    return "ok", "no run on record yet, and the project is younger than the cadence"


def evaluate(root: Path, today: _dt.date, reviews: list[dict],
             stamped: dict[str, _dt.date], born: _dt.date | None) -> list[dict]:
    rows = []
    for review in reviews:
        row = {"id": review["id"], "skill": review.get("skill", ""),
               "cadence": _cadence_text(review.get("cadence") or {})}
        last = last_run(root, review, stamped)
        row["last"] = str(last) if last else None
        if review.get("checked_by"):
            row["state"], row["detail"] = "elsewhere", f"reported by {review['checked_by']}"
        elif review.get("applies_if") and not (root / review["applies_if"]).exists():
            row["state"], row["detail"] = "n/a", f"does not apply: {review['applies_if']} is absent"
        elif born is None:
            row["state"], row["detail"] = "n/a", "no diamonds yet, so nothing is due"
        else:
            row["state"], row["detail"] = _judge(root, review, last, today, born)
        rows.append(row)
    return rows


def check_line(rows: list[dict]) -> str:
    due = [r for r in rows if r["state"] == "due"]
    if not due:
        judged = [r for r in rows if r["state"] in ("ok", "due")]
        return f"OK: {len(judged)} scheduled review(s) judged, none past its cadence."
    parts = [f"{r['id']} ({r['cadence']}; {r['detail']})" for r in due]
    return (f"SCHEDULED REVIEWS DUE — {len(due)} review(s) past their cadence: "
            + "; ".join(parts)
            + ". Run each skill, or /mycelium:feedback-review to see the whole schedule; a review "
            "run outside its skill is not seen until the skill records it.")


def _record(root: Path, reviews: list[dict], rid: str, when: str, note: str) -> int:
    if rid not in {r["id"] for r in reviews}:
        print(f"review_schedule: '{rid}' is not in the schedule (engine/review-schedule.yml).",
              file=sys.stderr)
        return 1
    path = root / RUNS_REL
    _state_dir.prepare_dir(path.parent)
    row = {"review": rid, "date": when, "note": note} if note else {"review": rid, "date": when}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"review_schedule: recorded {rid} on {when} in {RUNS_REL}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    ap.add_argument("--schedule", default=str(SCHEDULE),
                    help="the schedule file (tests point it elsewhere)")
    verb = ap.add_mutually_exclusive_group()
    verb.add_argument("--check", action="store_true", help="one advisory line (the default)")
    verb.add_argument("--list", action="store_true", help="the whole schedule, one row per review")
    verb.add_argument("--record", metavar="ID", help="append a run of ID to the run record")
    ap.add_argument("--date", help="with --record: the run's date (default today)")
    ap.add_argument("--note", default="", help="with --record: a short note")
    args = ap.parse_args(argv)

    root = Path(args.project_dir)
    reviews, err = load_schedule(Path(args.schedule))
    if err:
        print(f"UNREADABLE (review schedule did NOT run): {err}")
        return 0
    if args.record:
        return _record(root, reviews, args.record, args.date or args.today, args.note)
    stamped, err = stamps(root)
    born, err = (None, err) if err else oldest_diamond(root)
    if err:
        print(f"UNREADABLE (review schedule did NOT run): {err}")
        return 0
    rows = evaluate(root, _dt.date.fromisoformat(args.today), reviews, stamped, born)
    if args.list:
        for r in rows:
            last = r["last"] or "-"
            print(f"{r['id']:<20} {r['cadence']:<22} last {last:<11} {r['state']:<9} {r['detail']}")
        return 0
    print(check_line(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
