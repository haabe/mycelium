"""A NEXT ITEM routed to /mycelium:canvas-health must land on a check the skill runs (v0.328.5).

next_item.py's COMMANDS sends some advisories to /mycelium:canvas-health. Until v0.328.5 four of them
(stale-prose, unchecked-handle, source-class-fidelity, published-source-dead) were raised by scripts
the skill never named, so a person who followed the item ran the skill and never saw the record that
fired; on the dogfood project unchecked-handle came back for three sessions.

The map below names the script that raises each routed advisory. A new route to canvas-health with
no entry here fails the first test, and a script dropped from the skill fails the second, so a route
cannot again point at a skill that does not run its check.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
SKILL = ROOT / "plugins" / "mycelium" / "skills" / "canvas-health" / "SKILL.md"

#: advisory id -> the script whose output the advisory reports (read from hooks/session-start.sh).
RAISED_BY = {
    "idle-opportunities": "check_idle_opportunities.py",
    "evidence-landing-regressed": "check_evidence_landing.py",
    "stale-prose": "check_stale_prose.py",
    "unchecked-handle": "check_source_authenticity.py",
    "source-class-fidelity": "check_source_class_fidelity.py",
    "published-source-dead": "check_published_records.py",
}


def _routed_to_canvas_health():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import next_item

    return {aid for aid, (_text, cmd) in next_item.COMMANDS.items() if cmd == "/mycelium:canvas-health"}


def test_every_route_to_canvas_health_names_the_script_that_raises_it():
    routed = _routed_to_canvas_health()
    assert routed, "no advisory routes to canvas-health; this test would pass on nothing"
    assert routed == set(RAISED_BY), (
        f"routed but unmapped: {sorted(routed - set(RAISED_BY))}; "
        f"mapped but no longer routed: {sorted(set(RAISED_BY) - routed)}"
    )


def test_canvas_health_runs_every_script_a_route_sends_it_for():
    text = SKILL.read_text(encoding="utf-8")
    missing = sorted({s for s in RAISED_BY.values() if s not in text})
    assert not missing, f"canvas-health is routed advisories it never checks: {missing}"


def test_every_mapped_script_exists():
    absent = sorted({s for s in RAISED_BY.values() if not (SCRIPTS / s).is_file()})
    assert not absent, f"mapped to scripts that are not shipped: {absent}"
