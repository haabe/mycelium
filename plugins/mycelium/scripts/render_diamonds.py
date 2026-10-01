"""render_diamonds.py -- draw each diamond as the decisions it has recorded, in order, grouped by
mode (v0.309.0, phase migration stage 5d-3, founder ruling DL-1372 V4).

Until v0.309.0 /mycelium:diamond-render asked the agent to draw four phases (Discover, Define,
Develop, Deliver) as states with transition labels of its own, and listed seven test fixtures that
did not exist. The record is a decision log (DL-1368), so the picture is that log: each decision as
recorded, with its date, under the mode the diamond was in when it was taken (discovery until
`commit_to_build`, delivery after: DL-1368 S1), then the decisions still to come. A loop iterates
by appending (DL-1373), so a second `start_experiment` is drawn as a second step, where it happened.
An L0 is not a loop (DL-1368 S2): it states its purpose and reviews it.

Read-only. Drawn by code, so two renders of one record are the same picture.

    python3 render_diamonds.py --project-dir . [--format mermaid|ascii|json]
        [--scale active|all|L0..L5] [--theme base|dark] [--no-gates] [--no-confidence]

Exit 0 on a render (including "no open diamond"); 2 when the diamonds file cannot be read, a scale
is asked that has no diamond, or the format is not one of the three.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from . import scale_locks as sl
except ImportError:  # invoked as a script, or loaded by file path
    import scale_locks as sl

#: The loop's decisions in order (DL-1366). An L0 has its own two (DL-1368 S2).
LOOP = ("set_target", "start_experiment", "commit_to_build", "release", "close")
FORMATS = ("mermaid", "ascii", "json")
#: WCAG AA by construction (engine/render-conventions.md#wcag-aa-theme-convention); the tests run
#: validate_mermaid.py over the output.
_THEME = """---
config:
  theme: base
  themeVariables:
    primaryColor: '#ffffff'
    primaryTextColor: '#1a1a1a'
    primaryBorderColor: '#333333'
    lineColor: '#1a1a1a'
---"""
_THEME_DARK = "---\nconfig:\n  theme: dark\n---"
_CLASSES = (
    "  classDef current fill:#fff9c4,stroke:#3e2723,color:#3e2723,stroke-width:3px\n"
    "  classDef upcoming fill:#ffffff,stroke:#5f5f5f,color:#3d3d3d,stroke-dasharray:4 3")
NO_DIAMOND = "No open diamond: run /mycelium:start."


def _scale(d: dict) -> str:
    return str(d.get("scale") or "").strip().upper()


def _mapping(value) -> dict:
    return value if isinstance(value, dict) else {}


def _mode(made: list[str], scale: str) -> str:
    """The mode a diamond is in once `made` is recorded. A `close` is taken in the mode before it,
    so the caller passes the decisions before the close when it asks where the close belongs."""
    if scale == "L0":
        return "purpose"
    if "close" in made:
        return "closed"
    return "delivery" if "commit_to_build" in made else "discovery"


def _gates(scale: str, decision: str, statuses: dict, ai: bool) -> str:
    return ", ".join(f"{g} {statuses.get(g) or 'pending'}"
                     for g in sl.decision_gates(scale, decision, ai=ai))


def diamond_view(d: dict, ai: bool) -> dict:
    """One diamond as data: where it is, what it decided and when, what comes next."""
    scale = _scale(d)
    status = {str(k): str(v).split("#")[0].strip()
              for k, v in _mapping(d.get("theory_gates_status")).items()}
    recorded, made = [], []
    for e in sl.decisions_of(d):
        dec = str(e["decision"])
        mode = _mode(made if dec == "close" else [*made, dec], scale)
        made.append(dec)
        relied = {str(k): str(v) for k, v in _mapping(e.get("gates")).items()}
        recorded.append({"decision": dec, "on": str(e["on"])[:10] if e.get("on") else None,
                         "reconstructed": bool(e.get("reconstructed")), "mode": mode,
                         "gates": _gates(scale, dec, {**status, **relied}, ai)})
    if scale == "L0":
        todo, repeatable = ([] if "state_purpose" in made else ["state_purpose"]), ["review"]
    else:
        todo, repeatable = [x for x in LOOP if x not in made], []
    upcoming, so_far = [], list(made)
    for dec in todo:
        upcoming.append({"decision": dec,
                         "mode": _mode(so_far if dec == "close" else [*so_far, dec], scale),
                         "gates": _gates(scale, dec, status, ai)})
        so_far.append(dec)
    return {"id": str(d.get("id")), "scale": scale,
            "name": str(d.get("name") or d.get("title") or d.get("id")),
            "position": sl.position(d), "mode": _mode(made, scale),
            "confidence": d.get("confidence"), "parent": d.get("parent") or d.get("parent_id"),
            "created_at": str(d["created_at"])[:10] if d.get("created_at") else None,
            "recorded": recorded, "upcoming": upcoming, "repeatable": repeatable}


def select(project_dir: str, scale: str) -> list[dict]:
    st = sl.State(project_dir)
    # Every diamond the file holds (active, completed, archived), the active ones first.
    active_ids = [str(d.get("id")) for d in st.active]
    every = [st.by_id[i] for i in dict.fromkeys(active_ids + list(st.by_id)) if i in st.by_id]
    if scale == "active":
        picked = [d for d in st.active if st.is_open(d)]
    elif scale == "all":
        picked = every
    else:
        picked = [d for d in every if _scale(d) == scale]
    return [diamond_view(d, st.ai) for d in picked]


def _when(r: dict) -> str:
    return (r.get("on") or "date not recorded") + (" (reconstructed)" if r.get("reconstructed")
                                                     else "")


def _steps(v: dict, conf: bool) -> dict[str, list[dict]]:
    """The diamond's steps grouped by mode, in order: recorded, then still to come."""
    groups: dict[str, list[dict]] = {}
    last = len(v["recorded"])
    for i, r in enumerate(v["recorded"], 1):
        text = f"{r['decision']} {_when(r)}"
        if conf and i == last and v["confidence"] is not None:
            text += f" conf={v['confidence']}"
        groups.setdefault(r["mode"], []).append(
            {"text": text, "cls": "current" if i == last else "", "gates": r["gates"]})
    for u in v["upcoming"]:
        groups.setdefault(u["mode"], []).append(
            {"text": f"{u['decision']} (next)", "cls": "upcoming", "gates": u["gates"]})
    return groups


def _mermaid_diamond(did: str, v: dict, conf: bool) -> list[str]:
    out = [f'  state "{v["scale"]} {v["name"]}: {v["position"]}" as {did} {{', "    direction LR"]
    groups, n, prev = _steps(v, conf), 0, None
    for m, (mode, members) in enumerate(groups.items(), 1):
        mid = f"{did}_m{m}"
        out.append(f'    state "{mode}" as {mid} {{')
        for j, s in enumerate(members):
            n += 1
            s["id"] = f"{did}_{n}"
            out.append(f"      {s['id']} : {s['text']}")
            out.append(f"      [*] --> {s['id']}" if j == 0
                       else f"      {members[j - 1]['id']} --> {s['id']}")
        # Inside the mode's block: a `class` naming a state from the enclosing scope declares it
        # again there, and Mermaid draws it outside its mode (seen on the first render). Gates are
        # not drawn as notes: Mermaid places a note on a nested state across the page, between
        # diamonds; the ascii and json formats carry them.
        out += [f"      class {s['id']} {s['cls']}" for s in members if s["cls"]]
        out.append("    }")
        if prev:
            out.append(f"    {prev} --> {mid}")
        prev = mid
    if not groups:
        out.append(f"    {did}_0 : no decision recorded")
    out.append("  }")
    return out


def mermaid(views: list[dict], theme: str, conf: bool) -> str:
    out = [_THEME_DARK if theme == "dark" else _THEME, "stateDiagram-v2", _CLASSES]
    ids = {v["id"]: f"D{n}" for n, v in enumerate(views, 1)}
    for v in views:
        out += _mermaid_diamond(ids[v["id"]], v, conf)
    out += [f"  {ids[v['parent']]} --> {ids[v['id']]} : opened {v['created_at'] or ''}".rstrip()
            for v in views if v["parent"] in ids]
    return "\n".join(out) + "\n"


def ascii_(views: list[dict], gates: bool, conf: bool) -> str:
    out = []
    for v in views:
        head = f"{v['scale']} {v['name']}: {v['position']}"
        if conf and v["confidence"] is not None:
            head += f"  conf={v['confidence']}"
        out += [head, "=" * min(len(head), 79)]
        for mode, members in _steps(v, False).items():
            out.append(f"  [{mode}]")
            for s in members:
                mark = "." if s["cls"] == "upcoming" else "*"
                out.append(f"    {mark} {s['text']}"
                           + (f"   gates: {s['gates']}" if gates and s["gates"] else ""))
        out += [f"    . {x} (when the purpose drifts)" for x in v["repeatable"]]
        if not v["recorded"] and not v["upcoming"]:
            out.append("    no decision recorded")
        out.append("")
    out.append("* recorded   . still to come. A loop iterates by appending a decision (DL-1373).")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project-dir", default=".")
    ap.add_argument("--format", default="mermaid")
    ap.add_argument("--scale", default="active")
    ap.add_argument("--theme", default="base", choices=("base", "dark"))
    ap.add_argument("--no-gates", action="store_true")
    ap.add_argument("--no-confidence", action="store_true")
    a = ap.parse_args(argv)
    if a.format not in FORMATS:
        print(f"FORMAT NOT SUPPORTED: {a.format}. diamond-render emits {', '.join(FORMATS)}; "
              "a state diagram does not map to a table or a list.", file=sys.stderr)
        return 2
    if a.scale not in ("active", "all", *sl.SCALES):
        print(f"UNKNOWN SCALE: {a.scale} (active, all, L0-L5)", file=sys.stderr)
        return 2
    try:
        views = select(a.project_dir, a.scale)
    except (sl.UnreadableError, sl.CannotCheckError) as e:
        print(f"CANNOT READ the diamonds: {e}", file=sys.stderr)
        return 2
    if not views:
        if a.scale in sl.SCALES:
            print(f"NO {a.scale} DIAMOND in .claude/diamonds/active.yml.", file=sys.stderr)
            return 2
        print(NO_DIAMOND)
        return 0
    gates, conf = not a.no_gates, not a.no_confidence
    if a.format == "json":
        print(json.dumps({"schema_version": 2, "render": "diamond", "drawn_from": "decisions",
                          "diamonds": views}, indent=2))
    elif a.format == "ascii":
        print(ascii_(views, gates, conf), end="")
    else:
        print(mermaid(views, a.theme, conf), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
