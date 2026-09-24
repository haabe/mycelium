"""When each diamond was last assessed, on the machine's clock (v0.250.0).

`next_item.py` proposes /diamond-progress for a diamond "ruled on before the newest evidence". It
compared `progression_ruled_at`, a date the agent TYPES, with file modification times, to the DAY.
Two clocks at day precision fail in ordinary use: evidence landing later on the day of a ruling is
never "since" it, and a typed date ahead of the machine's (a model misjudging today, or a date the
user stated) silences the diamond until the clock catches up. E2E run 19 went a month of pilot
evidence without the delivering diamond being proposed, because its ruling carried a world date the
file clock never reached.

This records, on every write to diamonds/active.yml, the machine time at which a diamond's phase,
`progression_ruled_at` or `progression_history` length changed, and the session that changed it.
`next_item.py` then compares machine time with machine time, to the second, and ignores files the
ruling session itself wrote (the agent that ruled had them in front of it).

State: `.claude/state/diamond-rulings.json`, `{id: {sig, ts, session}}`. A diamond first seen gets
`ts: null`: never ruled, or ruled at an unknown time. next_item then uses the diamond's own fields.
Stdlib plus PyYAML; without PyYAML it records nothing and next_item falls back to the typed date.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # SPEAKS: next_item falls back to the typed date, which is today's behaviour
    yaml = None

STATE = Path(".claude") / "state" / "diamond-rulings.json"


def signature(d: dict) -> str:
    """What changes when a diamond is assessed: its phase, its ruling date, its history length."""
    hist = d.get("progression_history")
    return "|".join((str(d.get("phase") or "discover").lower(),
                     str(d.get("progression_ruled_at") or "")[:10],
                     str(len(hist) if isinstance(hist, list) else 0)))


def load(root: Path) -> dict:
    try:
        data = json.loads((root / STATE).read_text())
    except (OSError, ValueError):
        return {}  # no record yet: every diamond falls back to its typed date
    return data if isinstance(data, dict) else {}


def record(root: Path, session: str, now: str | None = None) -> dict:
    """Update the record from the current diamonds file. Returns the new record."""
    active = root / ".claude" / "diamonds" / "active.yml"
    if yaml is None or not active.exists():
        return {}
    try:
        doc = yaml.safe_load(active.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError):
        return {}  # an unparseable file is the schema check's finding, reported at the same write
    now = now or _dt.datetime.now(tz=_dt.UTC).isoformat()
    old = load(root)
    new = {}
    for d in doc.get("active_diamonds") or [] if isinstance(doc, dict) else []:
        if not isinstance(d, dict) or not d.get("id"):
            continue
        did, sig = str(d["id"]), signature(d)
        prev = old.get(did)
        if prev is None:
            # First sight is not an assessment (v0.250.2). A never-ruled diamond has no time; one
            # already ruled has an unknown one. Either way `ts` is None and next_item uses what
            # the diamond says ("never assessed", or the typed date). 0.250.0 set `now` for a
            # never-ruled diamond, which read as "last assessed" and hid it until evidence landed.
            new[did] = {"sig": sig, "ts": None, "session": session}
        elif prev.get("sig") != sig:
            new[did] = {"sig": sig, "ts": now, "session": session}
        else:
            new[did] = prev
    try:
        (root / STATE).parent.mkdir(parents=True, exist_ok=True)
        (root / STATE).write_text(json.dumps(new, indent=1, sort_keys=True))
    except OSError:
        return new  # an unwritable state dir: next_item falls back to the typed date
    return new


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(data, dict):
        return 0
    ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    path = str(ti.get("file_path") or ti.get("path") or "")
    if not path.endswith("diamonds/active.yml"):
        return 0
    root = Path(path).resolve().parent.parent.parent
    record(root, str(data.get("session_id") or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
