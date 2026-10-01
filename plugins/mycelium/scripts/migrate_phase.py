#!/usr/bin/env python3
"""Move a project's diamonds from the phase to the decision log (v0.303.0, migration stage 5a).

Founder ruling DL-1368 S3: a migration script, offered by the next item and by /mycelium:setup, run
on request, the change shown before anything is written. It rewrites three things the phase
migration keeps reading through a translation until stage 5 removes it:

  1. THE PHASE, into dated decisions. Each move a diamond made becomes the decisions that move makes
     (`scale_locks.TRANSITION_DECISIONS`; an L0 that stated its purpose records `state_purpose`),
     dated from its `progression_history` entry where there is one, and marked `reconstructed`:
     the moves happened, so recording them is a fact, not a decision made now. The recorded
     `phase` stays until stage 5c; the derived one must equal it, or the diamond is not changed.
  2. `learning_delivery`, into an exposure record marked `reconstructed`. Its data class and
     consent are left empty, since nothing recorded them, so the release gate asks for them.
  3. THE OLD L2 AND L3 SHAPE (DL-1367 R4): an L2 on one opportunity gets `target` and, where the
     opportunity rolls up to one, its outcome as `object_ref`; an L3 on one solution gets
     `front_runner` and its opportunity as `object_ref`.

Nothing else changes, and the result is checked before it is written: it must parse, and the scale
locks must judge it as no move (`scale_locks.violations_between` reports nothing). Comments other
than the file's leading block are refused unless `--accept-comment-loss`: PyYAML does not keep them.

Exit codes: 0 done (or nothing to do); 1 refused (the locks object, a derived phase disagrees, or
comments would be lost); 2 no diamonds file or it does not parse.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scale_locks as sl  # where a diamond is, and the lock that judges the result
from safe_replace import write_checked  # parse-before-write for canvas text edits

_LISTS = ("active_diamonds", "completed_diamonds", "archived_diamonds")


def _history_date(d: dict, t: str) -> tuple[str | None, str | None]:
    """The date and ruling of the progression_history entry for transition `t`, if any."""
    want = t.replace("->", " ").split()
    for h in d.get("progression_history") or []:
        if not isinstance(h, dict):
            continue
        text = str(h.get("transition") or "").lower().replace("→", " ").replace("->", " ")
        if want in (text.split(), [str(h.get("from", "")).lower(), str(h.get("to", "")).lower()]):
            return (str(h.get("date") or "")[:10] or None), (h.get("ruling") or None)
    return None, None


def _decisions(d: dict, phase: str) -> list[dict]:
    """The decisions a diamond at `phase` has made, reconstructed from its history."""
    if sl.decisions_of(d) or phase == "discover":
        return []
    if sl._scale(d) == "L0":  # noqa: SLF001 - the one scale parser
        on, ruling = _history_date(d, "discover->define")
        return [{"decision": "state_purpose", "on": on, "ruling": ruling, "reconstructed": True}]
    out = []
    order = sl.PHASE_ORDER
    for k in range(order.index(phase)):
        t = f"{order[k]}->{order[k + 1]}"
        on, ruling = _history_date(d, t)
        out += [{"decision": dec, "on": on, "ruling": ruling, "reconstructed": True}
                for dec in sl.TRANSITION_DECISIONS[t]]
    return out


def _exposure(d: dict, today: str) -> dict | None:
    """A `learning_delivery` as an exposure record, when the diamond has none of its own."""
    ld = d.get("learning_delivery")
    if not isinstance(ld, dict) or not ld.get("audience") or d.get("exposures"):
        return None
    rec = {"recorded_at": today, "audience": ld.get("audience"), "channel": ld.get("means"),
           "until": ld.get("until"), "data": ld.get("data"), "started": ld.get("started"),
           "ended": ld.get("ended"), "changes": ld.get("changes"), "reconstructed": True,
           "note": ("moved from learning_delivery by migrate_phase.py; data class and consent "
                    "were never recorded, so the release gate asks for them")}
    return {k: v for k, v in rec.items() if v not in (None, "", [], {})}


def migrate(doc: dict, st: sl.State, today: str) -> tuple[dict, list[str], list[str]]:
    """(the migrated document, what changed per diamond, what could not be migrated)."""
    changes, problems = [], []
    for key in _LISTS:
        for d in doc.get(key) or []:
            if not isinstance(d, dict) or not d.get("id"):
                continue
            did, said = str(d["id"]), []
            phase = "complete" if key == "completed_diamonds" and not d.get("phase") \
                else sl.phase_of(d)
            decs = _decisions(d, phase)
            # An L0 does not close (DL-1368 S2): one recorded `complete` reads as its purpose in
            # force, `deliver`, once it records `state_purpose` (v0.305.0).
            l0_done = sl._scale(d) == "L0" and phase == "complete"  # noqa: SLF001
            if decs:
                trial = {**d, "decisions": decs}
                if sl.phase_of(trial) != ("deliver" if l0_done else phase):
                    problems.append(f"{did}: its decisions would read as `{sl.phase_of(trial)}`, "
                                    f"its phase says `{phase}`; left as it is")
                    continue
                d["decisions"] = decs
                dated = sum(1 for x in decs if x["on"])
                said.append(f"{len(decs)} decision(s) from its phase `{phase}` ({dated} dated "
                            "from its history, all marked reconstructed)"
                            + ("; an L0 does not close, so it now reads as its purpose in force"
                               if l0_done else ""))
            rec = _exposure(d, today)
            if rec:
                d["exposures"] = [rec]
                del d["learning_delivery"]
                said.append("learning_delivery -> an exposure record (data class and consent to "
                            "be recorded)")
            elif isinstance(d.get("learning_delivery"), dict) and d.get("exposures"):
                problems.append(f"{did}: has both learning_delivery and exposures; the exposure "
                                "record is read second, so reconcile them by hand")
            said += _reshape(d, st)
            if said:
                changes.append(f"{did} ({d.get('scale')}): " + "; ".join(said))
    return doc, changes, problems


def _reshape(d: dict, st: sl.State) -> list[str]:
    """The old one-object shape recorded as the new fields (DL-1367 R4)."""
    scale, said = sl._scale(d), []  # noqa: SLF001
    if scale == "L2" and not d.get("target"):
        opp = st.find_opportunity(d.get("object_ref"))
        if opp is not None:
            d["target"] = {"opportunity": opp.get("id"), "reconstructed": True}
            outcome = sl._ref_key(opp.get("rolls_up_to"))  # noqa: SLF001
            if outcome in {str(r.get("id")) for r in st.roots() if r.get("id")}:
                d["object_ref"] = outcome
                said.append(f"object_ref -> the outcome {outcome}, target -> {opp.get('id')}")
            else:
                said.append(f"target -> {opp.get('id')} (its outcome is not an id: object_ref "
                            "left for you to set)")
    if scale == "L3" and not d.get("front_runner"):
        key = sl._ref_key(d.get("object_ref"))  # noqa: SLF001
        opp = st.find_opportunity(key)
        if opp is not None and key != str(opp.get("id")):
            d["front_runner"] = key
            d["object_ref"] = opp.get("id")
            said.append(f"object_ref -> the target {opp.get('id')}, front_runner -> {key}")
    return said


def _split_header(text: str) -> tuple[str, list[str]]:
    """The leading comment block, and every other comment line."""
    lines = text.splitlines(keepends=True)
    k = 0
    while k < len(lines) and (lines[k].lstrip().startswith("#") or not lines[k].strip()):
        k += 1
    rest = [ln.rstrip() for ln in lines[k:] if ln.lstrip().startswith("#")]
    return "".join(lines[:k]), rest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--write", action="store_true", help="write the migrated file (default: show)")
    ap.add_argument("--accept-comment-loss", action="store_true")
    ap.add_argument("--today", default=_dt.datetime.now(tz=_dt.UTC).date().isoformat())
    args = ap.parse_args(argv)
    root = Path(args.project_dir).resolve()
    path = root / ".claude" / "diamonds" / "active.yml"
    try:
        before = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(before) or {}
    except (OSError, yaml.YAMLError) as e:
        print(f"migrate_phase: cannot read {path}: {e}")
        return 2
    header, comments = _split_header(before)
    st = sl.State(str(root))
    doc, changes, problems = migrate(doc, st, args.today)
    for p in problems:
        print(f"  NOT MIGRATED {p}")
    if not changes:
        print("migrate_phase: nothing to migrate" + (" (see above)" if problems else ""))
        return 1 if problems else 0
    after = header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    objections = sl.violations_between(str(root), before, after)
    for c in changes:
        print(f"  {c}")
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm=""))
    print(f"migrate_phase: {len(changes)} diamond(s); the file diff is {len(diff)} line(s)")
    if objections:
        print("REFUSED: the scale locks read the migrated file as a change:\n  "
              + "\n  ".join(objections))
        return 1
    if comments and not args.accept_comment_loss:
        print(f"REFUSED: {len(comments)} comment line(s) outside the leading block would be "
              "lost (PyYAML drops them); move them into the leading block or pass "
              "--accept-comment-loss:\n  " + "\n  ".join(comments[:5]))
        return 1
    if not args.write:
        print("Dry run: nothing written. Run again with --write to write it.")
        return 0
    write_checked(path, after)
    print(f"migrate_phase: written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
