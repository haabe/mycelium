"""The pages a newcomer reads name every switch and every state file the plugin has (v0.322.2).

WHAT WAS WRONG. `docs/environment.md` opened with "Every `MYCELIUM_*` environment variable in one
place" and named 9 of the 28 `MYCELIUM_*` names the plugin tree uses. Three of the missing ones
loosen a stop (`MYCELIUM_GUARD_STATE_EDIT`, `MYCELIUM_NEXT_ACTION_CHECK`, `MYCELIUM_TODAY`). `PRIVACY.md`
lists what the hooks keep under `.claude/state/` and left out the files that are not logs, among
them `session-checks.json`, which holds the full text of a session's reminders. Both were found by
a blind read of 0.321.0: three readers compared what the pages say with what the code does.

WHAT HOLDS NOW. A name the plugin tree uses must be on the page, so the next variable or state
file added without a line there fails here. These tests check that a name is PRESENT. They cannot
check that what the page says about it is true; that is what a reader is for.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
ENV_PAGE = ROOT / "docs" / "environment.md"
PRIVACY = ROOT / "PRIVACY.md"

TEXT = {".sh", ".py", ".json", ".txt", ".md", ".ts", ".yml", ".yaml"}
VARIABLE = re.compile(r"MYCELIUM_[A-Z0-9_]*[A-Z0-9]")
STATE_FILE = re.compile(r"\.claude/state/([A-Za-z0-9_*-]+(?:\.[A-Za-z0-9_*-]+)*)")
#: PRIVACY.md covers every hook's fire log with one row, "the other `*-fires.jsonl`".
FIRE_LOG = "-fires.jsonl"


def _files(*tops: str):
    for top in tops:
        for f in sorted((PLUGIN / top).rglob("*")):
            if f.is_file() and f.suffix in TEXT:
                yield f


def _read(f: Path) -> str:
    try:
        return f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _variables() -> dict[str, str]:
    found: dict[str, str] = {}
    for f in _files("hooks", "scripts", "skills", "integrations", "engine"):
        for name in VARIABLE.findall(_read(f)):
            found.setdefault(name, str(f.relative_to(ROOT)))
    return found


def _state_files() -> dict[str, str]:
    found: dict[str, str] = {}
    for f in _files("hooks", "scripts"):
        for name in STATE_FILE.findall(_read(f)):
            found.setdefault(name, str(f.relative_to(ROOT)))
    return found


def test_every_variable_the_plugin_names_is_on_the_environment_page():
    """RED BEFORE 0.322.2: nineteen names were missing, three of them switches that loosen a stop."""
    page = ENV_PAGE.read_text()
    missing = {n: where for n, where in _variables().items() if n not in page}
    assert missing == {}, f"not on docs/environment.md: {missing}"


def test_the_switches_that_loosen_a_stop_are_said_to():
    """Being listed is not enough for these: the row and PRIVACY.md both say what they loosen."""
    env, privacy = ENV_PAGE.read_text(), PRIVACY.read_text()
    for name in ("MYCELIUM_GUARD_STATE_EDIT", "MYCELIUM_NEXT_ACTION_CHECK", "MYCELIUM_TODAY"):
        row = next(line for line in env.splitlines() if line.startswith(f"| `{name}`"))
        assert "oosen" in row, f"{name}: its row does not say it loosens a stop"
        assert name in privacy, f"{name}: not named in PRIVACY.md"
    assert "docs/environment.md" in privacy


def test_every_state_file_the_hooks_name_is_on_the_privacy_page():
    """RED BEFORE 0.322.2: `session-checks.json`, `next-item.json` and ten more had no line."""
    page = PRIVACY.read_text()
    missing = {n: where for n, where in _state_files().items()
               if n not in page and not n.endswith(FIRE_LOG)}
    assert missing == {}, f"not in PRIVACY.md: {missing}"
    assert "*" + FIRE_LOG in page, "the row that covers the fire logs is gone"


def test_control_the_scans_find_names_known_to_be_there():
    """If the scans found nothing, every test above would pass on an empty page."""
    assert "MYCELIUM_CI_SIGNAL" in _variables()
    assert "MYCELIUM_GUARD_STATE_EDIT" in _variables()
    assert {"read-log.jsonl", "session-checks.json", "discovery-skip-ack"} <= set(_state_files())
