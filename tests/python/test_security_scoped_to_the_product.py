"""Security and privacy checks are scoped to what the product holds and does (v0.271.0).

Founder, 2026-09-26: "2fa and so on might not be applicable for all products." The E2E second world,
a bookkeeping service delivered by hand, was reviewed against the OWASP web checklist (CORS, SQL
parameters, security headers, multi-factor login); theory-gates.md said a purely offline service's
Security gate was N/A, which the lock cannot honour; and the product-type "conditioning" it cited
existed nowhere in the product-type profiles.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"


def _text(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_the_review_records_its_scope_before_its_checklist():
    skill = _text("skills/security-review/SKILL.md")
    step0, checklist = skill.index("## Step 0: Scope"), skill.index("## Checklist (OWASP")
    assert step0 < checklist, "the scope comes first"
    for field in ("runs_code", "accounts", "personal_data", "money", "reach"):
        assert field in skill[step0:checklist], field
    assert "applies when `runs_code`" in skill, "the web checklist is scoped to code"
    assert "Authentication items (A07: sessions, passwords, multi-factor) | `accounts`" in skill
    assert "`n/a: <reason>`" in skill and "The threat model is never `n/a`" in skill
    assert "Documents and data handled by people" in skill, "a service has its own section"


def test_privacy_controls_are_proportional():
    skill = _text("skills/privacy-check/SKILL.md")
    assert "- [ ] Encryption at rest and in transit\n" not in skill
    assert "encryption where personal data is stored or sent electronically" in skill
    assert "holds no personal data, say so in the data inventory" in skill


def test_the_gate_text_matches_what_the_lock_enforces():
    gates = _text("engine/theory-gates.md")
    assert "If purely offline service, this gate is N/A" not in gates, "the lock cannot honour N/A"
    assert "the gate is never N/A" in gates
    assert "conditioned on product_type" not in _text("engine/confidence-thresholds.yml")


def test_the_scope_has_a_place_in_the_threat_model_schema():
    import json
    schema = json.loads(_text("schemas/canvas/threat-model.schema.json"))
    scope = schema["properties"]["security_scope"]["properties"]
    assert set(scope) == {"runs_code", "accounts", "personal_data", "money", "reach"}
    doc = yaml.safe_load("security_scope:\n  runs_code: false\n  accounts: false\n"
                         "  personal_data: client bank exports\n  money: true\n"
                         "  reach: three named clients\n")
    assert isinstance(doc["security_scope"]["runs_code"], bool)


def test_a_threat_model_that_says_its_scope_in_words_stays_valid(tmp_path):
    """0.271.0 defined `scope` as an object, and the E2E service world's threat model, which
    wrote its scope as a sentence ("Three pilot clients, one live month ...") as the threat-model
    skill's first step asks, failed the canvas check on the next write. v0.271.1."""
    import os
    import subprocess
    import sys
    canvas = tmp_path / ".claude" / "canvas"
    canvas.mkdir(parents=True)
    (canvas / "threat-model.yml").write_text(yaml.safe_dump({
        "scope": "Three pilot clients, one live month, documents by file share",
        "security_scope": {"runs_code": False, "accounts": True,
                           "personal_data": "client bank exports", "money": True,
                           "reach": "three named clients"},
        "threats": [{"id": "T1", "description": "a summary sent to the wrong client"}]}))
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_canvas.py")],
                       cwd=tmp_path, capture_output=True, text=True, check=False,
                       env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)})
    errors = [ln for ln in (r.stdout + r.stderr).splitlines() if "threat-model.yml ::" in ln]
    assert not [ln for ln in errors if "scope" in ln], errors
