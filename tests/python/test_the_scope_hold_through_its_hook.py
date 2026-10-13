"""The scope hold, called the way the runtime calls it, and the pages that describe it (v0.324.0).

WHAT WAS WRONG. Until 0.324.0 `hooks/scope-gate.sh` held the agent's writes to the paths named in
`.claude/state/active-execution.json` and left at once when that file was absent. No skill, script
or hook wrote the file, so in a plugin install the hold was never on. A blind reader of the
installed plugin found it (dogfood 2026-10-11), and 0.323.2 made every page say so.

WHAT HOLDS NOW. A delivery cycle (an L4) names its folders on its own record when it commits to
build (`in_scope_paths` in `.claude/diamonds/active.yml`); the person is asked. While the cycle is
open a write outside them is put to the person, and refused where nobody is asked. The old file is
no longer read, and refuses product writes while it exists.

THE FOURTEEN STEPS are the bar the idea was held to before it was built (dogfood 2026-10-13): one
delivery cycle followed from the write that names its folders to the write after its close, through
the hook only, with the tool call on stdin. They were first replayed against a scratch copy; this
is the same sheet against the shipped hook, so a release in which any step answers differently does
not go out.

THIS FILE REPLACES the 0.323.2 test that held the pages to "the check is not switched on". That
test was built to fail on the day something shipped began to write the field, and said what to do
then: take the admissions out of the pages in the same release and rewrite the test for what the
hold does. Both are done here. It still holds the pages and the plugin together, both ways: the
pages may describe the hold only while a skill tells the agent to write the field, the schema
declares it, and session start says when a cycle names nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "mycelium"
HOOKS = PLUGIN / "hooks"
REC = ".claude/diamonds/active.yml"
OLD_STATE = ".claude/state/active-execution.json"

sys.path.insert(0, str(PLUGIN / "scripts"))
import advisory_ledger  # noqa: E402
import scope_check  # noqa: E402

BASE = """active_diamonds:
- id: l0-purpose
  scale: L0
  decisions:
  - {decision: state_purpose, on: '2026-10-01'}
- id: l4-billing
  scale: L4
  name: Billing delivery
  decisions:
  - {decision: set_target, on: '2026-10-10'}
completed_diamonds: []
archived_diamonds: []
"""
TARGET = "  - {decision: set_target, on: '2026-10-10'}\n"
COMMIT = ("  - {decision: start_experiment, on: '2026-10-13'}\n"
          "  - {decision: commit_to_build, on: '2026-10-13'}\n")
RELEASE = "  - {decision: release, on: '2026-10-14'}\n"
FOLDERS = "  in_scope_paths: [app/billing/, tests/billing/]\n"
COMMITTED = BASE.replace(TARGET + "completed", TARGET + COMMIT + FOLDERS + "completed")
TWO = BASE.replace(
    TARGET + "completed",
    TARGET + COMMIT + "  in_scope_paths: [app/billing/]\n"
    "- id: l4-search\n  scale: L4\n  name: Search delivery\n  decisions:\n"
    "  - {decision: set_target, on: '2026-10-11'}\n"
    "  - {decision: start_experiment, on: '2026-10-12'}\n"
    "  - {decision: commit_to_build, on: '2026-10-12'}\n"
    "  in_scope_paths: [app/search/]\ncompleted")


def _project(tmp_path: Path, record: str | None = BASE) -> Path:
    for sub in (".claude/canvas", ".claude/diamonds", ".claude/state", "app/billing", "app/users",
                "app/search", "tests/billing"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    if record is not None:
        (tmp_path / REC).write_text(record)
    for rel in ("app/billing/existing.py", "app/users/existing.py"):
        (tmp_path / rel).write_text("x = 1\ny = 2\n")
    return tmp_path


def _env(project: Path, **extra: str) -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "HOME": str(project), "TMPDIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(PLUGIN),
            "PYTHONUSERBASE": site.getuserbase(), **extra}


def _call(project: Path, tool: str, tool_input: dict, mode: str = "default",
          **extra: str) -> tuple[str, str]:
    """One tool call through hooks/scope-gate.sh. Returns (allow | ask | deny, the reason)."""
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
               "permission_mode": mode, "cwd": str(project), "session_id": "replay"}
    done = subprocess.run(["bash", str(HOOKS / "scope-gate.sh")], input=json.dumps(payload),
                          text=True, capture_output=True, env=_env(project, **extra), cwd=project,
                          timeout=60, check=False)
    assert done.returncode == 0 and not done.stderr.strip(), (done.returncode, done.stderr[:300])
    if not done.stdout.strip():
        return "allow", ""
    said = json.loads(done.stdout)["hookSpecificOutput"]
    return said["permissionDecision"], said["permissionDecisionReason"]


def _write(project, rel, mode="default", **extra):
    return _call(project, "Write", {"file_path": str(project / rel), "content": "z = 3\n"}, mode,
                 **extra)


def _edit(project, rel, old, new, mode="default"):
    return _call(project, "Edit", {"file_path": str(project / rel), "old_string": old,
                                   "new_string": new}, mode)


def _multi(project, rel):
    return _call(project, "MultiEdit", {"file_path": str(project / rel), "edits": [
        {"old_string": "x = 1", "new_string": "x = 10"},
        {"old_string": "y = 2", "new_string": "y = 20"}]})


def _shell(project, command):
    return _call(project, "Bash", {"command": command})


def _land(project: Path, old: str, new: str) -> None:
    """Stand in for the tool after a yes: put the text in the record."""
    text = (project / REC).read_text()
    assert text.count(old) == 1, (old, text.count(old))
    (project / REC).write_text(text.replace(old, new))


# ---------------------------------------------------------------- the fourteen steps


def test_the_fourteen_steps_of_one_delivery_cycle(tmp_path):
    """One cycle, from the write that names its folders to the write after its close. Every
    answer is collected before anything is asserted, so a failure names each step that differs."""
    p = _project(tmp_path / "main")
    sheet: list[tuple[object, str, str, tuple[str, str], tuple[str, ...]]] = []

    def row(step, what, want, got, must_say=()):
        sheet.append((step, what, want, got, must_say))

    naming = (TARGET + "completed", TARGET + COMMIT + FOLDERS + "completed")
    row(1, "the write that names two folders and commits the cycle to build", "ask",
        _edit(p, REC, *naming), ("l4-billing", "app/billing/", "tests/billing/"))
    _land(p, *naming)
    row(2, "inside: a new file written", "allow", _write(p, "app/billing/new.py"))
    row(3, "inside: an existing file edited", "allow",
        _edit(p, "app/billing/existing.py", "x = 1", "x = 10"))
    row(4, "inside: one call carrying several edits", "allow",
        _multi(p, "app/billing/existing.py"))
    row(5, "inside: a shell redirect into a file", "allow",
        _shell(p, "echo ok > tests/billing/out.txt"))
    row(6, "outside: a new file written", "ask", _write(p, "app/users/new.py"),
        ("'app/users/new.py'",))
    row(7, "outside: an existing file edited", "ask",
        _edit(p, "app/users/existing.py", "x = 1", "x = 10"), ("'app/users/existing.py'",))
    row(8, "outside: one call carrying several edits", "ask",
        _multi(p, "app/users/existing.py"), ("'app/users/existing.py'",))
    row(9, "outside: a shell redirect into a file", "ask",
        _shell(p, "echo ok > app/users/out.txt"), ("'app/users/out.txt'",))
    row(10, "outside: a path that starts inside and climbs out with ..", "ask",
        _write(p, "app/billing/../users/climb.py"), ("'app/users/climb.py'",))
    row(11, "step 6's write in a mode where no person is asked", "deny",
        _write(p, "app/users/new.py", mode="bypassPermissions"),
        ("'app/users/new.py'", "say yes to this write", "change the folders"))
    row(12, "a write under .claude/ with the hold on", "allow",
        _write(p, ".claude/canvas/notes.yml"))

    # The close, recorded the way the product records it (skills/diamond-progress step 9b):
    # `release` is its own earlier write; at `close` the decision is added, `completed_at` and
    # `dod_verdict` are written, and the cycle is MOVED to `completed_diamonds`. The line naming
    # the folders travels with it and nobody takes it away.
    last = TARGET + COMMIT
    row("12a", "the write that records the release", "allow", _edit(p, REC, last, last + RELEASE))
    _land(p, last, last + RELEASE)
    row("12b", "released and not yet closed: step 6's write", "ask",
        _write(p, "app/users/new.py"), ("'app/users/new.py'",))
    cycle = ("- id: l4-billing\n  scale: L4\n  name: Billing delivery\n  decisions:\n"
             + last + RELEASE + FOLDERS)
    closing = (cycle + "completed_diamonds: []\n",
               "completed_diamonds:\n"
               + cycle.replace(RELEASE, RELEASE + "  - {decision: close, on: '2026-10-15'}\n")
               + "  completed_at: '2026-10-15'\n  dod_verdict:\n"
                 "    signal_observed: invoices went out from the new module for a week\n"
                 "    verified_by: test\n")
    row("13a", "the write that closes the cycle: moved to the completed list, folders line intact",
        "allow", _edit(p, REC, *closing))
    _land(p, *closing)
    assert FOLDERS in (p / REC).read_text(), "the fixture must leave the folders line in the record"
    row(13, "after the close: step 6's write", "allow", _write(p, "app/users/new.py"))
    row(14, "a project where no delivery cycle has named folders: step 6's write", "allow",
        _write(_project(tmp_path / "none-open"), "app/users/new.py"))

    wrong = [f"step {step} ({what}): wanted {want}, got {got[0]}"
             + (f"; the message lacks {[w for w in must_say if w not in got[1]]}"
                if any(w not in got[1] for w in must_say) else "")
             for step, what, want, got, must_say in sheet
             if got[0] != want or any(w not in got[1] for w in must_say)]
    assert not wrong, "\n".join(wrong)
    assert [s for s, *_ in sheet if isinstance(s, int)] == list(range(1, 15))


# ---------------------------------------------------------------- beside the fourteen


def test_committing_to_build_with_nothing_said_is_refused_and_no_hold_is_an_answer(tmp_path):
    p = _project(tmp_path)
    decision, reason = _edit(p, REC, TARGET + "completed", TARGET + COMMIT + "completed")
    assert decision == "deny" and "in_scope_paths: []" in reason
    no_hold = (TARGET + "completed", TARGET + COMMIT + "  in_scope_paths: []\n" + "completed")
    decision, reason = _edit(p, REC, *no_hold)
    assert decision == "ask" and "has no hold" in reason
    _land(p, *no_hold)
    assert _write(p, "app/users/new.py") == ("allow", "")


def test_two_cycles_and_one_of_them_closes(tmp_path):
    p = _project(tmp_path, TWO)
    assert _write(p, "app/search/x.py") == ("allow", "")
    assert _write(p, "app/users/x.py")[0] == "ask"
    search_last = "  - {decision: commit_to_build, on: '2026-10-12'}\n"
    _land(p, search_last, search_last + RELEASE + "  - {decision: close, on: '2026-10-15'}\n")
    decision, reason = _write(p, "app/search/x.py")
    assert decision == "ask" and "'app/search/x.py'" in reason and "l4-search" not in reason
    decision, reason = _edit(p, REC, "  in_scope_paths: [app/billing/]\n",
                             "  in_scope_paths: [app/billing/, app/users/]\n")
    assert decision == "ask" and "l4-billing" in reason and "app/users/" in reason


def test_a_record_that_cannot_be_read_refuses_product_writes_only(tmp_path):
    p = _project(tmp_path, TWO + "  this line: [is not closed\n")
    decision, reason = _write(p, "app/users/x.py")
    assert decision == "deny" and "cannot be read" in reason
    assert _write(p, ".claude/canvas/n.yml") == ("allow", "")


def test_a_runtime_that_cannot_ask_refuses_the_outside_write(tmp_path):
    p = _project(tmp_path, COMMITTED)
    decision, reason = _write(p, "app/users/new.py", MYCELIUM_RUNTIME="codex")
    assert decision == "deny" and "'app/users/new.py'" in reason
    assert _write(p, "app/billing/new.py", MYCELIUM_RUNTIME="codex") == ("allow", "")


def test_in_a_project_as_setup_leaves_it_the_hold_says_nothing(tmp_path):
    """No diamonds file at all, and no old state file: every write passes this gate."""
    assert _write(_project(tmp_path, None), "app/users/new.py") == ("allow", "")


@pytest.mark.parametrize("held", [
    "  in_scope_paths: [app/billing/]\n",
    "  'in_scope_paths': [app/billing/]\n",
    '  "in_scope_paths":\n  - app/billing/\n',
    "  in_scope_paths: [ app/billing/ ]   # billing only\n",
])
def test_the_shell_s_early_exit_does_not_skip_a_hold_however_it_is_written(tmp_path, held):
    """The hook leaves before starting Python when the record names no folder. That check is a
    grep, so it is held to every way YAML can write the same list."""
    p = _project(tmp_path, BASE.replace(TARGET + "completed", TARGET + COMMIT + held + "completed"))
    assert _write(p, "app/users/new.py")[0] == "ask"


@pytest.mark.parametrize("empty", ["  in_scope_paths: []\n", "  in_scope_paths: [ ]  # none\n"])
def test_an_empty_list_holds_nothing_through_the_hook(tmp_path, empty):
    p = _project(tmp_path, BASE.replace(TARGET + "completed", TARGET + COMMIT + empty + "completed"))
    assert _write(p, "app/users/new.py") == ("allow", "")


def test_without_its_helper_the_hook_refuses_and_does_not_point_at_the_old_file(tmp_path):
    """Until 0.324.0 this refusal said to delete the old state file "to disable scope
    enforcement". That file is no longer read, so deleting it disables nothing. A reader of the
    release candidate found the sentence by reading the hook."""
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN / "hooks", plugin / "hooks")
    shutil.copytree(PLUGIN / "scripts", plugin / "scripts",
                    ignore=shutil.ignore_patterns("scope_check.py", "__pycache__"))
    p = _project(tmp_path / "project", COMMITTED)
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write", "permission_mode": "default",
               "cwd": str(p), "session_id": "s1",
               "tool_input": {"file_path": str(p / "app/users/new.py"), "content": "x"}}
    env = _env(p)
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin)
    done = subprocess.run(["bash", str(plugin / "hooks" / "scope-gate.sh")],
                          input=json.dumps(payload), text=True, capture_output=True, env=env,
                          cwd=p, timeout=60, check=False)
    assert done.returncode == 0, done.stderr[:300]
    said = json.loads(done.stdout)["hookSpecificOutput"]
    assert said["permissionDecision"] == "deny"
    assert "scope_check.py not found" in said["permissionDecisionReason"]
    assert "active-execution" not in said["permissionDecisionReason"]
    assert "disable" not in said["permissionDecisionReason"]


# ---------------------------------------------------------------- the old state file


@pytest.mark.parametrize("content", ['{"diamond_id": "l4-billing", "in_scope_paths": ["app/**"]}',
                                     "{not json"])
def test_an_old_state_file_refuses_product_writes_and_says_what_to_do(tmp_path, content):
    """Maintainer's ruling 2026-10-13: stop reading it, and refuse loudly, so that a hold someone
    set by hand is not dropped in silence. What it holds makes no difference."""
    p = _project(tmp_path, COMMITTED)
    (p / OLD_STATE).write_text(content)
    for rel in ("app/billing/new.py", "app/users/new.py"):
        decision, reason = _write(p, rel)
        assert decision == "deny" and "is no longer read" in reason and "in_scope_paths" in reason
    assert _write(p, ".claude/canvas/n.yml") == ("allow", "")


def test_the_logs_no_longer_read_the_old_state_file(tmp_path):
    """Until 0.324.0 both logs took a `diamond_id` label from it. Nothing reads it now."""
    p = _project(tmp_path)
    (p / OLD_STATE).write_text('{"diamond_id": "l4-billing"}')
    for hook, tool, log in (("change-log.sh", "Write", "change-log.jsonl"),
                            ("read-log.sh", "Read", "read-log.jsonl")):
        payload = {"tool_name": tool, "session_id": "s1",
                   "tool_input": {"file_path": str(p / "app/billing/existing.py"), "content": "x"}}
        done = subprocess.run(["bash", str(HOOKS / hook)], input=json.dumps(payload), text=True,
                              capture_output=True, env=_env(p), cwd=p, timeout=60, check=False)
        assert done.returncode == 0, done.stderr[:300]
        rows = [json.loads(line) for line in (p / ".claude/state" / log).read_text().splitlines()]
        assert rows and rows[-1]["file_path"].endswith("existing.py"), rows
        assert all("diamond_id" not in r for r in rows), rows


# ---------------------------------------------------------------- session start


def test_session_start_names_a_cycle_that_committed_with_nothing_said(tmp_path):
    """Every delivery cycle that was open when 0.324.0 arrived: not held, and the person is told
    at session start, where it is read, and not only on a write that never comes."""
    p = _project(tmp_path, BASE.replace(TARGET + "completed", TARGET + COMMIT + "completed"))
    (p / OLD_STATE).write_text("{}")
    done = subprocess.run(["bash", str(HOOKS / "session-start.sh")],
                          input=json.dumps({"hook_event_name": "SessionStart", "session_id": "s1",
                                            "cwd": str(p)}),
                          text=True, capture_output=True, env=_env(p), cwd=p, timeout=180,
                          check=False)
    assert done.returncode == 0, done.stderr[:300]
    said = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "SCOPE HOLD: delivery cycle(s) l4-billing committed to build" in said
    assert f"SCOPE HOLD: {OLD_STATE} is no longer read" in said


def test_session_start_says_nothing_about_a_cycle_that_named_its_folders(tmp_path):
    p = _project(tmp_path, COMMITTED)
    done = subprocess.run(["bash", str(HOOKS / "session-start.sh")],
                          input=json.dumps({"hook_event_name": "SessionStart", "session_id": "s1",
                                            "cwd": str(p)}),
                          text=True, capture_output=True, env=_env(p), cwd=p, timeout=180,
                          check=False)
    assert done.returncode == 0, done.stderr[:300]
    assert "SCOPE HOLD" not in done.stdout


def test_the_advisory_ledger_counts_both_notices(tmp_path):
    """A reminder the ledger cannot count is one nobody can rule on or snooze."""
    p = _project(tmp_path, BASE.replace(TARGET + "completed", TARGET + COMMIT + "completed"))
    (p / OLD_STATE).write_text("{}")
    found = advisory_ledger.scan(scope_check.notices(str(p)))
    assert {"scope-hold-old-state-file", "scope-hold-nothing-said"} <= set(found)


# ---------------------------------------------------------------- the pages and the plugin


#: page -> the words it must carry while the hold is read from the delivery cycle's record.
MUST_SAY = {
    "docs/ai-system-card.md": "holds only where folders were named",
    "docs/context-surface.md": "A write outside the folders an open delivery cycle named",
    "PRIVACY.md": "the folder names go into your git history",
    "plugins/mycelium/hooks/README.md": "On the delivery cycle's own record",
    "plugins/mycelium/skills/diamond-progress/SKILL.md":
        "An L4's `commit_to_build` says where the work may write",
    ".claude/state/README.md": "is retired (0.324.0)",
}
#: page -> the 0.323.2 admission that is no longer true, or the older words that sent the
#: reader to a skill for a file no skill wrote.
MUST_NOT_SAY = {
    "docs/ai-system-card.md": "The scope check is not switched on by anything Mycelium ships",
    "docs/context-surface.md": "nothing Mycelium ships writes that file",
    "PRIVACY.md": "Paths the scope check would hold the agent's writes to",
    "plugins/mycelium/hooks/README.md": "That is every plugin install today",
    ".claude/state/README.md": "is written by nothing Mycelium ships",
    "plugins/mycelium/scripts/scope_check.py": "run /diamond-progress",
}
#: What makes the hold real in a plugin install. If one of these goes, the pages above describe
#: something that is not there, which is the state 0.323.2 had to correct.
WIRED = {
    "skills/diamond-progress/SKILL.md": "in_scope_paths: [app/billing/, tests/billing/**]",
    "schemas/diamonds/active.schema.json": '"in_scope_paths": {',
    "hooks/session-start.sh": '"$SCOPE_CHECK" --notices "$PROJECT_DIR"',
    "hooks/scope-gate.sh": ".claude/diamonds/active.yml",
    "engine/agent-operating-contract.md": "`in_scope_paths` on an L4",
}
#: The plugin files that name the old state file. Each either says it is retired, lists it among
#: the files that are the person's to write, or refuses while it exists. None reads what is in it.
NAMES_THE_OLD_FILE = {
    "engine/agent-operating-contract.md",
    "hooks/README.md",
    "hooks/change-log.sh",
    "hooks/guard-state-gate.sh",
    "hooks/read-log.sh",
    "hooks/scope-gate.sh",
    "schemas/diamonds/active.schema.json",
    "scripts/_hook_input.py",
    "scripts/scope_check.py",
    "skills/diamond-progress/SKILL.md",
}


@pytest.mark.parametrize("page", sorted(MUST_SAY))
def test_the_page_says_what_the_hold_does(page):
    assert MUST_SAY[page] in (ROOT / page).read_text(), (
        f"{page} no longer says what the scope hold does since 0.324.0.")


@pytest.mark.parametrize("page", sorted(MUST_NOT_SAY))
def test_the_page_no_longer_admits_a_hole_that_is_closed(page):
    assert MUST_NOT_SAY[page] not in (ROOT / page).read_text(), (
        f"{page} still says the scope check is off, or sends the reader to a skill for the old "
        "state file. A page that admits a hole that has been closed is as untrue as one that "
        "hides it.")


@pytest.mark.parametrize("rel", sorted(WIRED))
def test_what_the_pages_describe_is_wired_in_the_plugin(rel):
    assert WIRED[rel] in (PLUGIN / rel).read_text(), (
        f"{rel} no longer carries `{WIRED[rel]}`. The pages describe a hold that a delivery cycle "
        "switches on by naming its folders; without this, nothing in a plugin install does, and "
        "the pages have to say so again (MUST_SAY above).")


def test_nothing_new_in_the_plugin_names_the_old_state_file():
    found = set()
    for path in PLUGIN.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "active-execution" in text:
            found.add(path.relative_to(PLUGIN).as_posix())
    new = found - NAMES_THE_OLD_FILE
    assert not new, (
        f"new in the plugin, naming the retired state file: {sorted(new)}. It is read by nothing "
        "since 0.324.0. If this file reads it, the pages are wrong again; if it only mentions "
        "it, add it to NAMES_THE_OLD_FILE with the reason.")
