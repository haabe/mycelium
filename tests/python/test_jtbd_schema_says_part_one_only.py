"""The JTBD canvas says it carries part 1 of the job spec only (founder ruling 2026-11-12).

Candidate the-jtbd-schema-implements-one-fifth-of-the-books-job-spec: Competing Against Luck's job
spec has five parts (the dimensions, tradeoffs, competing solutions, obstacles and anxieties, the
experiences of purchase and use), and the shipped schema carries the first. The ruling was "Say
it's part 1 only": no new fields, and both the skill and the schema description say what is left
out, so a reader does not take a recorded job for a full spec.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
SCHEMA = PLUGIN / "schemas" / "canvas" / "jobs-to-be-done.schema.json"
SKILL = PLUGIN / "skills" / "jtbd-map" / "SKILL.md"

LEFT_OUT = (
    "tradeoffs the customer is willing to make",
    "competing solutions that must be beaten",
    "obstacles and anxieties that must be overcome",
    "experiences of purchase and use",
)


def test_schema_description_says_part_one_only_and_names_the_rest():
    desc = " ".join(json.loads(SCHEMA.read_text(encoding="utf-8"))["description"].split())
    assert "PART 1 OF THE JOB SPEC ONLY" in desc
    for part in LEFT_OUT:
        assert part in desc, part


def test_skill_says_part_one_only_and_names_the_rest():
    text = " ".join(SKILL.read_text(encoding="utf-8").split())
    assert "## What the canvas holds: part 1 of the job spec only" in text
    for part in LEFT_OUT:
        assert part in text, part


def test_no_job_spec_field_was_added():
    """The ruling adds no fields; a later change that adds them should come with its own ruling."""
    job = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]["jobs"]["items"]
    for name in ("tradeoffs", "competing_solutions", "obstacles_anxieties", "experience"):
        assert name not in job["properties"], name
