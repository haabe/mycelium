"""Integrity guard for the AI System Card template + Mycelium's own card.

Why this exists: from ~v0.20 to v0.32 the AI System Card *template* was referenced
in four places (`/xai-check` Stage 4, `engine/xai-canvas-threading.md`, the card
footer, `manifest.yml`'s `.claude/templates/` entry) but the file was never
created — `/xai-check` Stage 4 reads "the template's Required markings", so the
skill pointed at a missing file for weeks with nothing to catch it. These tests
fail if the template or any Required section disappears again.

Canonical source is `plugins/mycelium/templates/ai-system-card.md` (installed to
`.claude/templates/`); Mycelium's filled instance is `docs/ai-system-card.md`.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "plugins" / "mycelium" / "templates" / "ai-system-card.md"
CARD = REPO / "docs" / "ai-system-card.md"

# Sections /xai-check Stage 4 treats as Required for a limited+ tier `pass`.
REQUIRED_SECTIONS = [
    "1. Identity",
    "2. Intended use",
    "3. Model details",
    "4. Performance and limitations",
    "5. Explainability",
    "6. Recourse",
    "7. Privacy and data handling",
    "10. Contact and feedback",
]


def _heading_line(text: str, title: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("## ") and title in line:
            return line
    return None


def test_template_exists():
    assert TEMPLATE.exists(), (
        "AI System Card template missing — /xai-check Stage 4 references it. "
        "Expected at plugins/mycelium/templates/ai-system-card.md."
    )


def test_card_exists():
    assert CARD.exists(), "Mycelium's own AI System Card (docs/ai-system-card.md) is missing."


def test_template_marks_every_required_section():
    text = TEMPLATE.read_text(encoding="utf-8")
    for title in REQUIRED_SECTIONS:
        line = _heading_line(text, title)
        assert line is not None, f"template missing required section: {title}"
        assert "Required" in line, (
            f"template section '{title}' is not marked Required — "
            "/xai-check Stage 4 reads these markings"
        )


def test_card_contains_every_required_section():
    text = CARD.read_text(encoding="utf-8")
    for title in REQUIRED_SECTIONS:
        assert _heading_line(text, title) is not None, (
            f"docs/ai-system-card.md missing required section: {title}"
        )


def test_xai_check_template_reference_resolves():
    """The path /xai-check Stage 4 names must resolve to the canonical template."""
    skill = (REPO / "plugins" / "mycelium" / "skills" / "xai-check" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "templates/ai-system-card.md" in skill, (
        "xai-check Stage 4 no longer references the template — update this guard if intentional"
    )
    # Runtime path is .claude/templates/...; canonical source is plugins/mycelium/templates/...
    assert TEMPLATE.exists()
