"""The verbs the open item offers record only what the ledger accepts.

Dogfood L1 assessment, 2026-10-14: the founder answered the session-start item "rule it: does not
choose a path". The agent line said `--ruling ...` after offering "run, rule, snooze until a date,
or drop", so the agent ran `advisory_ledger.py rule --id fired:ht-123 --ruling rule`, which exited 2
("ruling must be one of keep, fix, drop, snooze"). "run" and "rule" mapped to no ledger value.
next_item.OFFER now maps each offered verb to the ledger values it records; these tests hold the
mapping, every line that names a `--ruling` value, and the ledger's accepted set together.
"""

from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "mycelium" / "scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location("next_item", SCRIPTS / "next_item.py")
ni = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ni)
import advisory_ledger as al  # noqa: E402

L0 = "product_paths: []\nactive_diamonds:\n  - id: l0-x\n    scale: L0\n    phase: discover\n"
_RULING_VALUE = re.compile(r"--ruling ([^\s`]+)")


def _project(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "diamonds").mkdir(parents=True)
    (tmp_path / ".claude" / "diamonds" / "active.yml").write_text(L0)
    return tmp_path


def _session(root: Path, session: str, today: str, monkeypatch) -> dict:
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    monkeypatch.setattr("sys.stdout", io.StringIO())
    ni.main(["--project-dir", str(root), "--session", session, "--today", today, "--write-state"])
    return json.loads((root / ni.STATE_REL).read_text())


def _named_rulings(line: str) -> set[str]:
    """Every value a line tells the agent to pass as --ruling (`keep|fix` names two)."""
    return {v for m in _RULING_VALUE.findall(line) for v in m.split("|")}


def test_the_ledger_values_the_offer_records_are_exactly_what_the_ledger_accepts():
    recorded = {r for _, rulings, _ in ni.OFFER for r in rulings}
    assert recorded == set(al.RULINGS)


def test_the_human_line_offers_the_verbs_the_table_maps():
    line = ni.render_human({"id": "x", "text": "Do the thing.", "command": "/mycelium:x"})
    offered = line.split("Do the thing. ", 1)[1].rstrip(".").split(" | ")
    assert tuple(part.split()[0].split("-")[0] for part in offered) == ni.OFFERED_VERBS


def test_every_ruling_a_line_names_is_one_the_ledger_accepts(tmp_path, monkeypatch):
    root = _project(tmp_path)
    for i, day in enumerate(("2026-09-24", "2026-09-25", "2026-09-26")):
        _session(root, f"s{i}", day, monkeypatch)
    prompt = ni.prompt_line(root)
    answer = ni.answer_line(root, "snooze it until 2026-10-26")
    agent = ni.render({"id": "x", "text": "Do the thing.", "command": "/mycelium:x"})
    for line in (prompt, answer, agent):
        assert line, "the line under test was not produced"
        named = _named_rulings(line)
        assert named, line
        assert named <= set(al.RULINGS), (named - set(al.RULINGS), line)
    # The prompt line offers the verbs, so it carries how each one is recorded.
    for verb in ni.OFFERED_VERBS:
        assert f"{verb}: " in prompt


def test_each_value_the_offer_records_is_accepted_by_the_ledger(tmp_path):
    (tmp_path / ".claude" / "state").mkdir(parents=True)
    for _, rulings, _ in ni.OFFER:
        for r in rulings:
            msg = al.rule(tmp_path, "x", r, "their words", "2026-10-14",
                          "2026-10-20" if r == "snooze" else "")
            assert " ruled " in msg, msg
    # and the word that was refused on 2026-10-14 is still refused, so the table is what saves it
    assert " ruled " not in al.rule(tmp_path, "x", "rule", "", "2026-10-14")
