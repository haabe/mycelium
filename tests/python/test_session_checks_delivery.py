"""The background session-start checks reach the session even when the first read fails.

session-start.sh --async writes the heavy tier's text to .claude/state/session-checks.json and
preflight.sh delivers it at the next prompt, then marks it delivered. Until 0.334.1 both wrote the
file in place (`json.dump(d, open(path, "w"))`), so a prompt that arrived mid-write read an empty
or partial file; and on any failed read preflight printed "could not be delivered" and removed the
pending marker, so the session never got its checks (dogfood 2026-10-10: "JSONDecodeError: Extra
data", the file valid and complete minutes later).

Now both writers put a temporary file in the same folder and rename it over the old one, and a
failed read keeps the marker so the next prompt reads again; the line is printed once, after
three failed reads.
"""

import json
import os
import re
import site
import subprocess
import sys
import threading
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "mycelium"
SESSION_START = PLUGIN / "hooks" / "session-start.sh"
PREFLIGHT = PLUGIN / "hooks" / "preflight.sh"
LOST = "background session-start checks could not be delivered"
DELIVERED = "MYCELIUM FEEDBACK LOOPS (background run, delivered now)"


def _env(root: Path) -> dict:
    return {"CLAUDE_PROJECT_DIR": str(root), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
            "MYCELIUM_CROSS_REPO_WATCH": "", "MYCELIUM_SESSION_START_BUDGET": "600",
            "MYCELIUM_ADVISORY_LEDGER": "off", "TMPDIR": str(root), "HOME": str(root),
            "PYTHONUSERBASE": site.getuserbase(),
            "PATH": str(Path(sys.executable).parent) + os.pathsep + "/usr/bin:/bin"}


def _project(root: Path) -> Path:
    (root / ".claude" / "memory").mkdir(parents=True)
    (root / ".claude" / "canvas").mkdir(parents=True)
    (root / ".claude" / "state").mkdir(parents=True)
    (root / ".claude" / "memory" / "corrections.md").write_text("# corrections\n")
    (root / ".claude" / "canvas" / "opportunities.yml").write_text("opportunities: []\n")
    return root / ".claude" / "state"


def _cache(sid: str = "s1") -> str:
    return json.dumps({"fingerprint": "f", "session": sid, "generated_epoch": 1.0,
                       "generated_at": "2026-11-12T00:00:00Z",
                       "reminders": "OPEN human task: ht-1 is waiting. " * 40,
                       "delivered_to": None})


def _prompt(root: Path, sid: str = "s1") -> str:
    payload = json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": sid})
    done = subprocess.run(["bash", str(PREFLIGHT)], input=payload, capture_output=True,
                          text=True, env=_env(root), check=False, timeout=120)
    assert done.returncode == 0, done.stderr[-400:]
    return done.stdout


# --------------------------------------------------------------------------- a failed read retries

def test_a_file_unreadable_at_the_first_prompt_is_delivered_at_the_second(tmp_path):
    """RED ON 0.334.1: the first prompt printed the could-not-be-delivered line and removed the
    marker, so the second prompt, with the file whole, delivered nothing."""
    state = _project(tmp_path)
    (state / "session-checks.pending").write_text("s1")
    whole = _cache()
    (state / "session-checks.json").write_text(whole[: len(whole) // 2])
    first = _prompt(tmp_path)
    assert LOST not in first
    assert DELIVERED not in first
    assert (state / "session-checks.pending").read_text().splitlines()[0] == "s1"
    (state / "session-checks.json").write_text(whole)
    second = _prompt(tmp_path)
    assert DELIVERED in second
    assert "OPEN human task: ht-1" in second
    assert LOST not in second
    assert not (state / "session-checks.pending").exists()
    assert json.loads((state / "session-checks.json").read_text())["delivered_to"] == "s1"


def test_a_file_that_stays_unreadable_is_named_once_after_three_prompts(tmp_path):
    """RED ON 0.334.1: the line came at the first prompt, before any retry."""
    state = _project(tmp_path)
    (state / "session-checks.pending").write_text("s1")
    (state / "session-checks.json").write_text('{"session": "s1", "remi')
    said = [_prompt(tmp_path) for _ in range(4)]
    assert [LOST in s for s in said] == [False, False, True, False]
    assert "tried at 3 prompts" in said[2]
    assert not (state / "session-checks.pending").exists()


def test_control_a_file_from_an_older_session_waits_and_says_nothing(tmp_path):
    """GREEN ON 0.334.1 TOO: the background tier has not written this session's file yet."""
    state = _project(tmp_path)
    (state / "session-checks.pending").write_text("s2")
    (state / "session-checks.json").write_text(_cache("s1"))
    out = _prompt(tmp_path, "s2")
    assert LOST not in out
    assert DELIVERED not in out
    assert (state / "session-checks.pending").read_text() == "s2"


# --------------------------------------------------------------------------- writers replace whole

def _snippet(hook: Path, anchor: str) -> str:
    """The inline Python of `hook` that contains `anchor`, exactly as the hook runs it."""
    for code in re.findall(r"python3 -c '\n(.*?)\n' ", hook.read_text(), flags=re.DOTALL):
        if anchor in code:
            return code
    raise AssertionError(f"no inline python containing {anchor!r} in {hook.name}")


def test_both_writers_replace_the_file_rather_than_rewrite_it(tmp_path):
    """RED ON 0.334.1: written in place, the file kept its inode and was empty between the
    truncating open and the close. A rename gives it a new inode, which a reader never sees half
    written."""
    state = _project(tmp_path)
    cache = state / "session-checks.json"
    cache.write_text(_cache())
    before = cache.stat().st_ino
    subprocess.run([sys.executable, "-c", _snippet(SESSION_START, '"delivered_to": None'),
                    "fp", "s1", str(cache), "reminders"], check=True, timeout=60)
    after_start = cache.stat().st_ino
    assert after_start != before
    assert json.loads(cache.read_text())["session"] == "s1"
    subprocess.run([sys.executable, "-c", _snippet(PREFLIGHT, 'd["delivered_to"] = sid'),
                    "s1", str(cache)], check=True, timeout=60)
    assert cache.stat().st_ino != after_start
    assert json.loads(cache.read_text())["delivered_to"] == "s1"
    assert sorted(p.name for p in state.iterdir()) == ["session-checks.json"]


def test_a_reader_looping_during_rewrites_always_parses(tmp_path):
    """RED ON 0.334.1 (seen on the in-place writer: the reader caught an empty file)."""
    state = _project(tmp_path)
    cache = state / "session-checks.json"
    cache.write_text(_cache())
    writer = _snippet(SESSION_START, '"delivered_to": None')
    reminders = "OPEN human task: ht-1 is waiting. " * 200
    failures: list[str] = []
    stop = threading.Event()

    def read_loop():
        while not stop.is_set():
            try:
                json.loads(cache.read_text())
            except (ValueError, OSError) as e:
                failures.append(type(e).__name__)

    reader = threading.Thread(target=read_loop)
    reader.start()
    try:
        for _ in range(40):
            subprocess.run([sys.executable, "-c", writer, "fp", "s1", str(cache), reminders],
                           check=True, timeout=60)
    finally:
        stop.set()
        reader.join()
    assert failures == []


def test_the_async_tier_writes_the_file_through_the_hook(tmp_path):
    """The snippets above are cut from the hooks; this runs the hook itself once, so the cut
    cannot drift from what ships."""
    state = _project(tmp_path)
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup",
                          "session_id": "s9"})
    done = subprocess.run(["bash", str(SESSION_START), "--async"], input=payload,
                          capture_output=True, text=True, env=_env(tmp_path), check=False,
                          timeout=300)
    assert done.returncode == 0, done.stderr[-400:]
    assert json.loads((state / "session-checks.json").read_text())["session"] == "s9"
    assert not [p.name for p in state.iterdir() if p.name.endswith(".tmp")]
