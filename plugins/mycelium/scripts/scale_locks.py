#!/usr/bin/env python3
"""Entry locks between diamond scales: what a parent must have established before a child opens.

WHY THIS EXISTS (v0.245.0). The founder's model, restated 2026-09-24 when it was found missing:
*"all scales have a natural lock per se. It might be unwise to build a strategy unless you have a
purpose. It would be unwise to start looking into opportunities without knowing who to reach doing
what (L0+L1). And so on. There's a dependency tree."* `engine/diamond-rules.md` has said "L0 spawns
L1 when purpose is defined, L1 spawns L2 when landscape is mapped, L2 spawns L3 when opportunities
have sufficient evidence" since the plugin migration, and nothing read it. Then 0.217.0, 0.242.5 and
0.243.0 opened every door regardless of the parent, which turned a ruling about SPEED ("a child may
progress faster than its parent") into a ruling about ENTRY. With every scale open at once, nothing
stopped a user building the wrong thing straight away; an end-to-end dogfood run shipped a release
over 31 commits under an L0 in discover.

TWO QUESTIONS, NEVER ANSWERED WITH EACH OTHER:
  ENTRY: what must exist above a child before it opens (`entry=True`: the hook and --can-open).
  SPEED: once open, a diamond moves on its own gates, may be ahead of its parent and may revise it.
  So an opportunity closing AFTER its L3 opened (the normal state once shipped) re-locks nothing:
  the open-opportunity check is an entry check only. What stays true of an open cycle is that its
  chain still EXISTS: a purpose, an outcome, a target with evidence (`entry=False`: --check and the
  delivery gate's question, "may this cycle carry new code").

THE LOCKS. They read the parent's ARTEFACT at L1-L3 and a confidence band only at L4 and L5, because
that is where the sources put numbers: the ordering is top-down in every source read (Wardley p12,
Cagan Empowered p113-118, Torres CDH p27, Gilad Evidence-Guided p43), none of them locks the upper
levels on a score (Torres p35 and p101, Wardley p32: the levels are worked together and revise each
other), and Gilad's only thresholds are on ideas (launch at medium confidence or above, ICE Done
Right p14; medium-high before delivery for most ideas, Evidence-Guided p158-159).

  L1  a stated purpose: purpose.yml `why` (three words or more) and who it is for (`who`).
  L2  the L1 lock, plus a desired outcome, the root of the opportunity tree (Torres p27, p44-47):
      opportunities.yml `desired_outcome` (`.metric`, or a line) or a `desired_outcomes[].metric`.
  L3  the L2 lock, plus a chosen target opportunity with evidence behind it: the diamond's
      `object_ref` (or its L2 parent's) resolves to an opportunity with an evidence type above
      speculation AND a source it came from; at entry it must also be open, and name its root when
      the tree has more than one (Torres p101-107, Gilad Testing Product Ideas p9).
  L4  the L3 lock on the L3 it delivers (its `parent`, or the L3 with the same `object_ref`; never a
      killed or archived one), plus that L3's evidence at data-supported or better.
  L5  the L4 lock on its parent L4, that L4 shipped, and launch data (`launch_data`: usage, feedback
      or metric movement, on the L4 or the L5; Gilad Evidence-Guided p123).

WHAT THE LOCKS CANNOT DO. They check that the parent's artefact EXISTS, not that it is true: an
evidence type and a source are agent-writable fields. Requiring a named source makes an invented one
visible in review, and the E2E dogfood harness measures whether a builder invents them. Truth stays
with the evidence gates and the human.

OVERRIDE. One line per diamond in `.claude/state/scale-lock-ack`: `<id> <scale> <YYYY-MM-DD> <the
user's own words>`. Only a line in that shape counts, and only for that id AT that scale. The file
is guarded state (`_hook_input.GUARD_STATE_REL`): the agent writing it gets an ASK.

Exit codes: 0 holds / report clean; 1 a lock does not hold (reasons printed); 2 precondition or
bad input; 3 cannot check (PyYAML missing: printed, and repeated each prompt by hooks/preflight.sh).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # SPEAKS: every entry point returns exit 3 with the reason, see _require_yaml
    yaml = None

SCALES = ("L0", "L1", "L2", "L3", "L4", "L5")
DELIVERY_SCALES = ("L3", "L4", "L5")
CLOSED = {"complete", "completed", "killed", "parked", "archived"}
DEAD = {"killed", "archived"}
MEDIUM_OR_BETTER = {"data-supported", "test-validated", "launch-validated"}
CLOSED_OPPORTUNITY = {"closed", "discarded", "resolved", "addressed"}
SHIPPED_PHASES = {"deliver", "complete", "completed"}
ACK_REL = os.path.join(".claude", "state", "scale-lock-ack")
_MIN_PURPOSE_WORDS = 3
_BOOKKEEPING = {"source_class", "evidence_type", "validated", "_meta", "confidence", "captured_at"}
_WHO_KEYS = ("who", "target_users", "for_whom")
_ACK_LINE = re.compile(r"^\s*(\S+)\s+(L[0-5])\s+(\d{4}-\d{2}-\d{2})\s+\S", re.IGNORECASE)
_LISTS = ("active_diamonds", "completed_diamonds", "archived_diamonds")

EXIT_HOLDS, EXIT_LOCKED, EXIT_BAD, EXIT_CANNOT = 0, 1, 2, 3


class CannotCheckError(Exception):
    """The locks cannot be read on this machine (PyYAML absent)."""


class UnreadableError(Exception):
    """A state file exists and does not parse; the locks are unknown, and the caller must say so."""


class EditNotAppliedError(Exception):
    """The proposed edit does not apply to the file; the tool itself will refuse the write."""


# ---------------------------------------------------------------- reading


def _require_yaml():
    if yaml is None:
        raise CannotCheckError(
            "PyYAML is not installed (pip install pyyaml); scale locks are not checked")


def _parse(text: str, label: str):
    _require_yaml()
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise UnreadableError(f"{label} does not parse: {str(exc).splitlines()[0]}") from exc


def _load(project_dir: str, *rel: str):
    path = os.path.join(project_dir, ".claude", *rel)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except FileNotFoundError:
        return None  # SPEAKS: a missing file is a missing artefact, named by the lock that needs it
    except OSError as exc:
        raise UnreadableError(f"{'/'.join(rel)} cannot be read: {exc}") from exc
    return _parse(text, "/".join(rel))


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _words(value) -> int:
    return len(value.split()) if isinstance(value, str) else 0


def _filled(value) -> bool:
    """Something a reader could act on: a worded string, or a container holding one. Bookkeeping
    keys (source_class, validated, ...) do not count, so a `who:` holding only `validated: false`
    is empty."""
    if isinstance(value, str):
        return _words(value) > 0
    if isinstance(value, dict):
        return any(_filled(v) for k, v in value.items() if k not in _BOOKKEEPING)
    if isinstance(value, list):
        return any(_filled(v) for v in value)
    return False


def _ref_key(ref) -> str:
    """`opportunities.yml#sol-002, swap + approval` -> `sol-002`. One parser for every reference."""
    if ref is None or isinstance(ref, (dict, list)):
        return ""
    words = str(ref).split("#")[-1].split(",")[0].split()
    return words[0] if words else ""


def _scale(d: dict) -> str:
    return str(d.get("scale") or "").strip().upper()


def _read_acks(project_dir: str) -> tuple[set[tuple[str, str]], list[str]]:
    try:
        with open(os.path.join(project_dir, ACK_REL), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return set(), []  # SPEAKS: no ack file is no override, which is the locked direction
    acked, ignored = set(), []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _ACK_LINE.match(line)
        if m:
            acked.add((m.group(1), m.group(2).upper()))
        else:
            ignored.append(line.strip()[:80])
    return acked, ignored


class State:
    """Canvas and diamonds as the locks read them. `diamonds_doc` overrides active.yml, so a hook
    can judge the file a write WOULD produce before it lands."""

    def __init__(self, project_dir: str, diamonds_doc=None):
        _require_yaml()
        self.purpose = _as_dict(_load(project_dir, "canvas", "purpose.yml"))
        self.opps_doc = _as_dict(_load(project_dir, "canvas", "opportunities.yml"))
        if diamonds_doc is None:
            diamonds_doc = _load(project_dir, "diamonds", "active.yml") or {}
        if not isinstance(diamonds_doc, dict):
            raise UnreadableError("diamonds/active.yml is not a mapping")
        lists = {k: [d for d in _as_list(diamonds_doc.get(k)) if isinstance(d, dict)]
                 for k in _LISTS}
        self.active = lists["active_diamonds"]
        self.by_id = {str(d.get("id")): d
                      for k in reversed(_LISTS) for d in lists[k] if d.get("id")}
        self.completed_ids = {str(d.get("id")) for d in lists["completed_diamonds"]}
        self.archived_ids = {str(d.get("id")) for d in lists["archived_diamonds"]}
        self.acked, self.ack_ignored = _read_acks(project_dir)

    # ------------------------------------------------------------ artefacts

    def purpose_missing(self) -> list[str]:
        p = self.purpose
        nested = _as_dict(p.get("purpose"))
        why = [p.get("why"), nested.get("statement"), nested.get("why")]
        miss = []
        if not any(_words(w) >= _MIN_PURPOSE_WORDS for w in why):
            miss.append("a purpose statement: canvas/purpose.yml `why` (L0, /mycelium:start)")
        if not any(_filled(src.get(k)) for src in (p, nested) for k in _WHO_KEYS):
            miss.append("who it is for: canvas/purpose.yml `who` (the 'for whom' half of the "
                        "interview's first answer)")
        return miss

    def roots(self) -> list[dict]:
        many = [r for r in _as_list(self.opps_doc.get("desired_outcomes")) if isinstance(r, dict)]
        one = self.opps_doc.get("desired_outcome")
        if isinstance(one, str):
            one = {"metric": one}
        return many + ([one] if isinstance(one, dict) else [])

    def outcome_missing(self) -> list[str]:
        if any(_filled(r.get("metric")) for r in self.roots()):
            return []
        return [("a desired outcome, the root of the opportunity tree: canvas/opportunities.yml "
                 "`desired_outcome.metric` (Torres; /mycelium:ost-builder)")]

    def opportunities(self) -> list[dict]:
        out, stack = [], list(_as_list(self.opps_doc.get("opportunities")))
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                out.append(o)
                stack.extend(_as_list(o.get("sub_opportunities")))
        return out

    def find_opportunity(self, ref) -> dict | None:
        key = _ref_key(ref)
        if not key:
            return None
        opps = self.opportunities()
        for o in opps:
            if str(o.get("id", "")) == key:
                return o
        for o in opps:
            for s in _as_list(o.get("solutions")):
                if isinstance(s, dict) and str(s.get("id", "")) == key:
                    return o
        return None

    # ------------------------------------------------------------ locks

    def is_open(self, d: dict) -> bool:
        return (str(d.get("id")) not in self.completed_ids | self.archived_ids
                and str(d.get("phase", "")).lower() not in CLOSED
                and str(d.get("state", "")).lower() not in CLOSED)

    def _alive(self, d: dict) -> bool:
        return (str(d.get("id")) not in self.archived_ids
                and str(d.get("phase", "")).lower() not in DEAD
                and str(d.get("state", "")).lower() not in DEAD)

    def missing(self, d: dict, entry: bool = False, _seen: frozenset = frozenset()) -> list[str]:
        """Everything this diamond's lock still needs; empty when it holds. `entry` adds the checks
        that apply only at the moment of opening (the target opportunity is still open)."""
        scale = _scale(d)
        did = str(d.get("id", "?"))
        if did in _seen:
            return [f"{did}: its parent chain loops back on itself"]
        check = {
            "L0": lambda *_: [],
            "L1": lambda *_: self.purpose_missing(),
            "L2": lambda *_: self.purpose_missing() + self.outcome_missing(),
            "L3": self._l3_missing, "L4": self._l4_missing, "L5": self._l5_missing,
        }.get(scale)
        if check is None:
            return [f"{did}: a scale (L0-L5); it has `{d.get('scale')}`"]
        return check(d, entry, _seen | {did})

    def _l3_missing(self, d: dict, entry: bool, _seen: frozenset) -> list[str]:
        miss = self.purpose_missing() + self.outcome_missing()
        did = str(d.get("id", "?"))
        opp = self.find_opportunity(d.get("object_ref"))
        if opp is None:
            l2 = self._parent_at(d, "L2")
            opp = self.find_opportunity(l2.get("object_ref")) if l2 else None
        if opp is None:
            miss.append(f"{did}: a chosen target opportunity, named as `object_ref` (the "
                        "opportunity or solution id in canvas/opportunities.yml)")
            return miss
        oid = opp.get("id", opp.get("name", "?"))
        miss += self._evidence_missing(opp, oid)
        status = str(opp.get("status", "")).lower()
        if entry and status in CLOSED_OPPORTUNITY:
            miss.append(f"{oid}: an open opportunity (it is `{status}`)")
        roots = [r for r in self.roots() if r.get("id")]
        if entry and len(roots) > 1 and str(opp.get("rolls_up_to", "")) not in {
                str(r["id"]) for r in roots}:
            miss.append(f"{oid}: `rolls_up_to` naming which desired outcome it serves")
        return miss

    @staticmethod
    def _evidence_missing(opp: dict, oid) -> list[str]:
        prov = _as_dict(opp.get("provenance"))
        evid = opp.get("evidence")
        evid_d = _as_dict(evid)
        ev = str(prov.get("evidence_type") or evid_d.get("evidence_type")
                 or opp.get("evidence_type") or "none")
        sources = (prov.get("evidence_sources") or evid_d.get("sources")
                   or evid_d.get("evidence_sources") or (evid if isinstance(evid, list) else None))
        if ev in ("none", "speculation"):
            return [(f"{oid}: evidence behind the opportunity (now `{ev}`; anecdotal or better, "
                     "with its source, e.g. /mycelium:log-evidence after a conversation)")]
        if not _filled(sources):
            return [(f"{oid}: the source of its `{ev}` evidence: `provenance.evidence_sources` "
                     "naming where it came from (a conversation, a note, a record)")]
        return []

    def _l4_missing(self, d: dict, entry: bool, seen: frozenset) -> list[str]:
        l3 = self._parent_at(d, "L3")
        if l3 is None:
            return [f"{d.get('id')}: the L3 it delivers, named as `parent` (a live one)"]
        miss = self.missing(l3, entry, seen)
        ev = str(l3.get("evidence_type") or "none")
        if ev not in MEDIUM_OR_BETTER:
            miss.append(f"{l3.get('id')}: evidence at medium confidence or higher before "
                        f"delivery (now `{ev}`; needs data-supported, test-validated or "
                        "launch-validated, Gilad Evidence-Guided p158-159)")
        return miss

    def _l5_missing(self, d: dict, entry: bool, seen: frozenset) -> list[str]:
        l4 = self._parent_at(d, "L4")
        if l4 is None:
            return [f"{d.get('id')}: the L4 whose release this is, named as `parent`"]
        miss = self.missing(l4, entry, seen)
        shipped = (l4.get("completed_at") or str(l4.get("id")) in self.completed_ids
                   or str(l4.get("phase", "")).lower() in SHIPPED_PHASES)
        if not shipped:
            miss.append(f"{l4.get('id')}: shipped (phase deliver or complete) before its "
                        "launch opens an L5")
        data = {**_as_dict(l4.get("launch_data")), **_as_dict(d.get("launch_data"))}
        if not any(_filled(data.get(k)) for k in ("usage", "feedback", "metric_movement")):
            miss.append(f"{l4.get('id')}: launch data from its release in `launch_data` (usage, "
                        "feedback or metric_movement; Gilad Evidence-Guided p123)")
        return miss

    def _parent_at(self, d: dict, scale: str) -> dict | None:
        """The live diamond at `scale` this one names: by `parent`, else by a shared `object_ref`.
        Completed parents count (an L3 completes, its L4 delivers); killed or archived never do."""
        for key in ("parent", "parent_id"):
            p = self.by_id.get(str(d.get(key) or ""))
            if p is not None and _scale(p) == scale and self._alive(p):
                return p
        ref = _ref_key(d.get("object_ref"))
        if ref:
            for p in self.by_id.values():
                if _scale(p) == scale and _ref_key(p.get("object_ref")) == ref and self._alive(p):
                    return p
        return None

    def verdict(self, d: dict, entry: bool = False) -> tuple[bool, list[str]]:
        miss = self.missing(d, entry)
        return (not miss or (str(d.get("id")), _scale(d)) in self.acked), miss


# ---------------------------------------------------------------- questions


def delivery_state(project_dir: str) -> tuple[bool, str]:
    """May new source files be written? Only under an open L3, L4 or L5 whose chain holds."""
    st = State(project_dir)
    delivery = [d for d in st.active if _scale(d) in DELIVERY_SCALES and st.is_open(d)]
    if not delivery:
        return False, "no diamond that delivers (L3, L4 or L5) is open"
    reasons = []
    for d in delivery:
        ok, miss = st.verdict(d)
        if ok:
            return True, f"{d.get('id')} ({d.get('scale')}) holds its lock"
        reasons.append(f"{d.get('id')} ({d.get('scale')}) is missing:\n    - "
                       + "\n    - ".join(miss))
    return False, "\n  ".join(reasons)


def can_open(project_dir: str, scale: str, object_ref=None, parent=None) -> list[str]:
    st = State(project_dir)
    probe = {"id": "the new diamond", "scale": scale, "object_ref": object_ref, "parent": parent}
    return st.missing(probe, entry=True)


def report(project_dir: str) -> tuple[list[tuple[str, str, list[str], bool]], list[str]]:
    st = State(project_dir)
    rows = []
    for d in st.active:
        if st.is_open(d):
            ok, miss = st.verdict(d)
            rows.append((str(d.get("id")), str(d.get("scale")), miss, ok))
    return rows, st.ack_ignored


# ---------------------------------------------------------------- the hook


def _apply_edits(text: str, edits) -> str:
    for raw in _as_list(edits):
        e = _as_dict(raw)
        old = e.get("old_string", e.get("oldText"))
        new = e.get("new_string", e.get("newText"))
        if not isinstance(old, str) or not isinstance(new, str):
            raise EditNotAppliedError("an edit without old/new text")
        if old not in text:
            raise EditNotAppliedError("old text not found")
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def _same_file(path: str, target: str, project_dir: str) -> bool:
    """Case-, dot- and symlink-insensitive: `ACTIVE.yml` and `diamonds/./active.yml` on a
    case-insensitive volume are the same file, and a literal suffix match let both through."""
    if not path:
        return False
    p = path if os.path.isabs(path) else os.path.join(project_dir, path)
    if os.path.exists(p) and os.path.exists(target):
        return os.path.samefile(p, target)
    return os.path.normcase(os.path.realpath(p)).lower() == \
        os.path.normcase(os.path.realpath(target)).lower()


def _proposed_text(payload: dict, target: str, before: str, project_dir: str) -> str | None:
    """The file content the write would leave, or None when the write does not touch the file."""
    ti = _as_dict(payload.get("tool_input"))
    if _same_file(str(ti.get("destination") or ""), target, project_dir):  # move_file onto it
        src = str(ti.get("source") or "")
        src = src if os.path.isabs(src) else os.path.join(project_dir, src)
        with open(src, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if not _same_file(str(ti.get("file_path") or ti.get("path") or ""), target, project_dir):
        return None
    if "content" in ti:
        return str(ti["content"])
    if payload.get("tool_name") == "Edit":
        return _apply_edits(before, [ti])
    return _apply_edits(before, ti.get("edits"))


def new_diamond_violations(project_dir: str, payload: dict) -> list[str]:
    """For a write to diamonds/active.yml: each diamond the write OPENS whose entry lock does not
    hold. Opening means: a new id in the active list, an id rescaled, or an id moved back into the
    active list from completed or archived. A diamond already open at its scale is never re-judged
    here: editing its phase is its own speed."""
    target = os.path.join(project_dir, ".claude", "diamonds", "active.yml")
    try:
        with open(target, encoding="utf-8", errors="replace") as fh:
            before = fh.read()
    except OSError:
        before = ""  # no file yet: every diamond the write adds is new
    after = _proposed_text(payload, target, before, project_dir)
    if after is None:
        return []
    try:
        old_doc = _as_dict(_parse(before, "diamonds/active.yml")) if before else {}
    except UnreadableError:
        old_doc = {}  # a broken file is repaired by this write: judge every diamond in it
    new_doc = _parse(after, "the proposed diamonds/active.yml")  # raises: refused, see _run_hook
    if not isinstance(new_doc, dict):
        new_doc = {}
    was_open = {str(d.get("id")): _scale(d) for d in _as_list(old_doc.get("active_diamonds"))
                if isinstance(d, dict)}
    st = State(project_dir, diamonds_doc=new_doc)
    out = []
    for d in st.active:
        if was_open.get(str(d.get("id"))) == _scale(d) and _scale(d):
            continue
        ok, miss = st.verdict(d, entry=True)
        if not ok:
            out.append(f"{d.get('id')} ({d.get('scale')}) cannot open yet. Its parent has not "
                       "established:\n    - " + "\n    - ".join(miss))
    return out


# ---------------------------------------------------------------- cli

_GATE_TAIL = """
Each scale opens on what its parent has established (engine/diamond-rules.md, Entry locks):
L1 on a purpose, L2 on a desired outcome, L3 on a target opportunity with evidence, L4 on an L3 at
medium confidence, L5 on launch data. Produce what is missing, then retry; the lines above say which
skill does it. Once open, a diamond moves at its own speed.

Only if the USER explicitly wants this diamond opened anyway, they record it, one line per diamond
in .claude/state/scale-lock-ack: `<id> <scale> <YYYY-MM-DD> <their own words>`. Do not write that
file on your own judgement."""


def _run_hook(project_dir: str) -> int:
    try:
        violations = new_diamond_violations(project_dir, json.loads(sys.stdin.read() or "{}"))
    except (EditNotAppliedError, json.JSONDecodeError):
        return EXIT_HOLDS  # SPEAKS: a malformed payload or a non-applying edit is refused by the
        # tool itself, with its own message; this hook has nothing to judge
    except UnreadableError as exc:
        print(f"Mycelium scale lock: refused. {exc}. A diamonds file that does not parse cannot "
              "be checked, and every gate that reads it fails closed; write it whole.",
              file=sys.stderr)
        return 2
    if not violations:
        return EXIT_HOLDS
    print("Mycelium scale lock: this write opens a diamond before its parent is ready.\n\n"
          + "\n".join(violations) + "\n" + _GATE_TAIL, file=sys.stderr)
    return 2


def _run_can_open(args) -> int:
    scale = args.can_open.upper()
    if scale not in SCALES:
        print(f"unknown scale {args.can_open}", file=sys.stderr)
        return EXIT_BAD
    miss = can_open(args.project_dir, scale, args.object_ref, args.parent)
    if not miss:
        print(f"{scale} can open.")
        return EXIT_HOLDS
    print(f"{scale} cannot open yet. Missing:\n  - " + "\n  - ".join(miss))
    return EXIT_LOCKED


def _run_check(project_dir: str) -> int:
    rows, ignored = report(project_dir)
    for did, scale, miss, ok in rows:
        state = "holds" if not miss else ("overridden by the user" if ok else "LOCKED")
        print(f"{did} ({scale}): {state}" + "".join(f"\n    - {m}" for m in miss))
    for line in ignored:
        print(f"scale-lock-ack line ignored (not `<id> <scale> <YYYY-MM-DD> <words>`): {line}")
    if not rows:
        print("no open diamonds")
    return EXIT_LOCKED if any(not r[3] for r in rows) else EXIT_HOLDS


def _run(args) -> int:
    if args.hook:
        return _run_hook(args.project_dir)
    if args.delivery_state:
        ok, why = delivery_state(args.project_dir)
        print(why)
        return EXIT_HOLDS if ok else EXIT_LOCKED
    if args.can_open:
        return _run_can_open(args)
    return _run_check(args.project_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report every open diamond's lock")
    mode.add_argument("--delivery-state", action="store_true",
                      help="exit 0 if new code may be written")
    mode.add_argument("--can-open", metavar="SCALE", help="may a diamond at SCALE open now?")
    mode.add_argument("--hook", action="store_true",
                      help="PreToolUse payload on stdin; exit 2 blocks")
    ap.add_argument("--object-ref")
    ap.add_argument("--parent")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except CannotCheckError as exc:
        print(f"MYCELIUM: {exc}.")
        return EXIT_CANNOT
    except UnreadableError as exc:
        print(f"MYCELIUM: scale locks unknown: {exc}.")
        return EXIT_LOCKED


if __name__ == "__main__":
    sys.exit(main())
