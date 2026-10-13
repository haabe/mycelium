"""Coverage proofs for scope_check.py, the helper behind hooks/scope-gate.sh.

REWRITTEN FOR 0.324.0, and each earlier case was settled from the decision behind the change, not
from the new output. Until 0.324.0 the folders were read from `.claude/state/active-execution.json`.
They are now read from the delivery cycle's own record (`in_scope_paths` on an L4 in
`.claude/diamonds/active.yml`), a write outside them is put to the person instead of refused, and
the old file is no longer read: while one exists, product writes are refused and the refusal says
what to do (maintainer's rulings, dogfood 2026-10-13).

What became of the fourteen earlier cases:
- kept as they were, the behaviour is unchanged: no path in the input allows; a tool call that
  is not JSON is refused; the helper run without its arguments is refused.
- rewritten for the record: no state allows; inside allows; outside (now asked, refused where
  nobody is asked); an empty list holds nothing; `.claude/` is never held; one star stays in its
  folder; two stars cross folders.
- folded into one: a corrupt old file and an old file of the wrong shape. The old file's content
  is no longer read, so there is one behaviour left to check: it exists, so product writes are
  refused.
- retired with the behaviour they pinned: `out_of_scope_paths` taking precedence, and the list
  nested under `spec`. Both were shapes of the old file. The record carries one list of where a
  cycle may write.

Tests drive main() in-process (monkeypatched argv and stdin) so coverage sees the lines. Allow,
ask and refuse all exit 0; the decision is the JSON on stdout, or nothing.
"""
import io
import json
import subprocess
import sys

import pytest

COMMITTED = ("  - {decision: set_target, on: '2026-10-10'}\n"
             "  - {decision: start_experiment, on: '2026-10-13'}\n"
             "  - {decision: commit_to_build, on: '2026-10-13'}\n")
TARGET_ONLY = "  - {decision: set_target, on: '2026-10-10'}\n"
CLOSED = COMMITTED + ("  - {decision: release, on: '2026-10-14'}\n"
                      "  - {decision: close, on: '2026-10-15'}\n")


def cycle(cid="l4-billing", decisions=COMMITTED, folders="[app/billing/, tests/billing/]",
          extra=""):
    """One delivery cycle as it sits in the record. `folders=None` leaves the field out."""
    field = "" if folders is None else f"  in_scope_paths: {folders}\n"
    return f"- id: {cid}\n  scale: L4\n  decisions:\n{decisions}{field}{extra}"


def record(*cycles, completed="[]"):
    return ("active_diamonds:\n- id: l0-purpose\n  scale: L0\n  decisions:\n"
            "  - {decision: state_purpose, on: '2026-10-01'}\n" + "".join(cycles)
            + f"completed_diamonds: {completed}\narchived_diamonds: []\n")


@pytest.fixture
def project(tmp_path):
    for sub in (".claude/canvas", ".claude/diamonds", ".claude/state", "app/billing", "app/users"):
        (tmp_path / sub).mkdir(parents=True)
    return tmp_path


def _hold(project, text):
    (project / ".claude" / "diamonds" / "active.yml").write_text(text)
    return project


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import scope_check
    return scope_check


def _run(scripts_path, monkeypatch, capsys, project, hook_input, raw=None):
    """Drive scope_check.main(). Returns (decision or None, reason)."""
    monkeypatch.setattr(sys, "argv", ["scope_check.py",
                                      str(project / ".claude/state/active-execution.json"),
                                      str(project)])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(hook_input) if raw is None else raw))
    sc = _import(scripts_path)
    with pytest.raises(SystemExit) as ei:
        sc.main()
    assert ei.value.code == 0
    out = capsys.readouterr().out.strip()
    if not out:
        return None, ""
    said = json.loads(out)["hookSpecificOutput"]
    return said["permissionDecision"], said["permissionDecisionReason"]


def _write(project, rel, mode="default", content="x = 1\n"):
    return {"tool_name": "Write", "permission_mode": mode,
            "tool_input": {"file_path": str(project / rel), "content": content}}


def _edit_record(project, old, new, mode="default"):
    return {"tool_name": "Edit", "permission_mode": mode,
            "tool_input": {"file_path": str(project / ".claude/diamonds/active.yml"),
                           "old_string": old, "new_string": new}}


# ---------------------------------------------------------------- what is inside


@pytest.mark.parametrize(("rel", "pattern", "expected"), [
    ("app/billing/a.py", "app/billing/", True),
    ("app/billing/deep/a.py", "app/billing", True),
    ("app/billing", "app/billing/", True),
    ("app/billing-old/a.py", "app/billing", False),
    ("app/users/a.py", "app/billing/", False),
    ("README.md", "README.md", True),
    ("./app/billing/a.py", "./app/billing/", True),
    ("app/billing/a.py", "app/*", False),
    ("app/billing/a.py", "app/**", True),
    ("app/billing/a.py", "", False),
])
def test_inside_reads_a_folder_a_file_or_a_glob(scripts_path, rel, pattern, expected):
    assert _import(scripts_path).inside(rel, pattern) is expected


# ---------------------------------------------------------------- writes the hold judges


def test_no_record_and_no_old_file_allows(scripts_path, project, monkeypatch, capsys):
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


@pytest.mark.parametrize("folders", ["[app/billing/]", "[app/billing]", "['app/billing/**']"])
def test_a_write_inside_a_named_folder_allows(scripts_path, project, monkeypatch, capsys, folders):
    _hold(project, record(cycle(folders=folders)))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/billing/a.py")) == (None, "")


def test_a_write_outside_is_put_to_the_person_with_the_file_named(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py"))
    assert decision == "ask"
    assert "'app/users/a.py'" in reason and "l4-billing" in reason and "app/billing/" in reason


def test_a_path_that_climbs_out_is_named_as_where_it_lands(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _write(project, "app/billing/../users/climb.py"))
    assert decision == "ask" and "'app/users/climb.py'" in reason


def test_where_nobody_is_asked_an_outside_write_is_refused_with_the_two_ways(
        scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _write(project, "app/users/a.py", mode="bypassPermissions"))
    assert decision == "deny" and "'app/users/a.py'" in reason
    assert "say yes to this write in a session where they are asked" in reason
    assert "change the folders the delivery cycle names" in reason


def test_a_runtime_that_cannot_ask_refuses(scripts_path, project, monkeypatch, capsys):
    monkeypatch.setenv("MYCELIUM_RUNTIME", "codex")
    _hold(project, record(cycle()))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py"))
    assert decision == "deny" and "cannot ask a person" in reason


def test_an_empty_list_is_no_hold(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders="[]")))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


def test_a_write_under_claude_is_never_held(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    assert _run(scripts_path, monkeypatch, capsys, project,
                _write(project, ".claude/canvas/purpose.yml")) == (None, "")


def test_one_star_stays_in_its_folder(scripts_path, project, monkeypatch, capsys):
    """`app/billing/*` must not reach `app/billing/legacy/secret.py` (fnmatch would let it)."""
    _hold(project, record(cycle(folders="['app/billing/*']")))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/billing/a.py")) == (None, "")
    decision, _ = _run(scripts_path, monkeypatch, capsys, project,
                       _write(project, "app/billing/legacy/secret.py"))
    assert decision == "ask"


def test_two_stars_cross_folders(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders="['app/**']")))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/a/b/c/d.py")) == (None, "")


def test_a_cycle_that_has_not_committed_holds_nothing(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY)))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


@pytest.mark.parametrize("how", ["closed in place", "moved to the completed list", "parked"])
def test_a_cycle_that_is_no_longer_open_holds_nothing(scripts_path, project, monkeypatch, capsys, how):
    if how == "closed in place":
        text = record(cycle(decisions=CLOSED))
    elif how == "parked":
        text = record(cycle(extra="  state: parked\n"))
    else:
        text = record(completed="\n" + cycle(decisions=CLOSED).rstrip("\n")) + ""
    _hold(project, text)
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


def test_with_two_open_cycles_a_write_is_inside_when_it_is_inside_either(
        scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders="[app/billing/]"),
                          cycle(cid="l4-search", folders="[app/search/]")))
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/search/a.py")) == (None, "")
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py"))
    assert decision == "ask" and "l4-billing" in reason and "l4-search" in reason


@pytest.mark.parametrize("text", [
    "active_diamonds:\n- id: l4-billing\n  in_scope_paths: [app/\n  this: [is not closed\n",
    "- just\n- a list\n",
])
def test_a_record_that_cannot_be_read_refuses_and_says_so(scripts_path, project, monkeypatch, capsys, text):
    _hold(project, text)
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py"))
    assert decision == "deny" and "cannot be read" in reason
    assert _run(scripts_path, monkeypatch, capsys, project,
                _write(project, ".claude/canvas/purpose.yml")) == (None, "")


def test_an_empty_record_holds_nothing(scripts_path, project, monkeypatch, capsys):
    _hold(project, "")
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


def test_a_shell_redirect_is_judged_like_a_write(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    inside = {"tool_name": "Bash", "permission_mode": "default",
              "tool_input": {"command": "echo ok > tests/billing/out.txt"}}
    outside = {"tool_name": "Bash", "permission_mode": "default",
               "tool_input": {"command": "echo ok > app/users/out.txt"}}
    assert _run(scripts_path, monkeypatch, capsys, project, inside) == (None, "")
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, outside)
    assert decision == "ask" and "'app/users/out.txt'" in reason


def test_a_shell_write_the_hold_cannot_read_is_put_to_the_person(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    call = {"tool_name": "Bash", "permission_mode": "default",
            "tool_input": {"command": 'echo ok > "$OUT"'}}
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "ask" and "a target the hold cannot read" in reason


def test_a_write_that_lands_outside_the_project_is_put_to_the_person(
        scripts_path, project, monkeypatch, capsys, tmp_path_factory):
    _hold(project, record(cycle()))
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "a.py"
    call = {"tool_name": "Write", "permission_mode": "default",
            "tool_input": {"file_path": str(elsewhere), "content": "x"}}
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "ask" and "outside the project" in reason


def test_no_path_in_the_input_allows(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    assert _run(scripts_path, monkeypatch, capsys, project,
                {"tool_name": "Write", "tool_input": {}}) == (None, "")


def test_a_tool_call_that_is_not_json_is_refused(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle()))
    decision, _ = _run(scripts_path, monkeypatch, capsys, project, None, raw="not json at all")
    assert decision == "deny"


def test_run_without_its_arguments_it_refuses(scripts_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["scope_check.py"])
    sc = _import(scripts_path)
    with pytest.raises(SystemExit) as ei:
        sc.main()
    assert ei.value.code == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------- the old state file


@pytest.mark.parametrize("content", ['{"in_scope_paths": ["app/billing/**"]}', "{not json", '["a list"]', ""])
def test_while_an_old_state_file_exists_product_writes_are_refused(
        scripts_path, project, monkeypatch, capsys, content):
    """Whatever it holds: it is no longer read, and a hold someone set by hand must not be
    dropped in silence."""
    (project / ".claude/state/active-execution.json").write_text(content)
    for rel in ("app/billing/a.py", "app/users/a.py"):
        decision, reason = _run(scripts_path, monkeypatch, capsys, project, _write(project, rel))
        assert decision == "deny" and "is no longer read" in reason
        assert "in_scope_paths" in reason and "deletes the file" in reason
    assert _run(scripts_path, monkeypatch, capsys, project,
                _write(project, ".claude/canvas/purpose.yml")) == (None, "")


def test_writing_the_old_state_file_still_asks_the_person(scripts_path, project, monkeypatch, capsys):
    """It stays one of the files that are the person's to write: deleting it lifts a refusal."""
    decision, _ = _run(scripts_path, monkeypatch, capsys, project,
                       _write(project, ".claude/state/active-execution.json", content="{}"))
    assert decision == "ask"


# ---------------------------------------------------------------- writes to the record


def test_naming_the_folders_is_put_to_the_person(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    call = _edit_record(project, TARGET_ONLY,
                        COMMITTED + "  in_scope_paths: [app/billing/, tests/billing/]\n")
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "ask"
    assert "l4-billing" in reason and "app/billing/, tests/billing/" in reason


def test_committing_to_build_with_nothing_said_is_refused(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _edit_record(project, TARGET_ONLY, COMMITTED))
    assert decision == "deny" and "nothing said about where it may write" in reason
    assert "in_scope_paths: [folder/, other/]" in reason and "in_scope_paths: []" in reason


def test_saying_no_hold_is_put_to_the_person_too(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _edit_record(project, TARGET_ONLY, COMMITTED + "  in_scope_paths: []\n"))
    assert decision == "ask" and "has no hold" in reason


def test_changing_the_folders_while_the_hold_is_on_asks(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders="[app/billing/]")))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _edit_record(project, "in_scope_paths: [app/billing/]",
                                         "in_scope_paths: [app/billing/, app/users/]"))
    assert decision == "ask" and "app/billing/, app/users/" in reason


def test_taking_the_folders_off_a_cycle_asks(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders="[app/billing/]")))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project,
                            _edit_record(project, "  in_scope_paths: [app/billing/]\n", ""))
    assert decision == "ask" and "leaves nothing said" in reason


def test_removing_a_cycle_and_its_folders_asks(scripts_path, project, monkeypatch, capsys):
    one = cycle(folders="[app/billing/]")
    _hold(project, record(one))
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, _edit_record(project, one, ""))
    assert decision == "ask" and "removes delivery cycle l4-billing" in reason


def test_a_close_that_moves_the_cycle_with_its_folders_is_not_a_question(
        scripts_path, project, monkeypatch, capsys):
    """How the product records a close (skills/diamond-progress step 9b). The first build put
    this to the person as a change of folders; found when the replay closed a cycle the way the
    product does (dogfood 2026-10-13)."""
    one = cycle(folders="[app/billing/]")
    _hold(project, record(one))
    moved = ("completed_diamonds:\n" + cycle(decisions=CLOSED, folders="[app/billing/]")
             + "  completed_at: '2026-10-15'\n")
    call = _edit_record(project, one + "completed_diamonds: []\n", moved)
    assert _run(scripts_path, monkeypatch, capsys, project, call) == (None, "")


def test_a_cycle_that_committed_before_the_hold_existed_is_left_alone(
        scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(folders=None)))
    call = _edit_record(project, "- id: l4-billing\n", "- id: l4-billing\n  name: Billing\n")
    assert _run(scripts_path, monkeypatch, capsys, project, call) == (None, "")
    assert _run(scripts_path, monkeypatch, capsys, project, _write(project, "app/users/a.py")) == (None, "")


def test_where_nobody_is_asked_naming_the_folders_is_refused(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    call = _edit_record(project, TARGET_ONLY, COMMITTED + "  in_scope_paths: [app/billing/]\n",
                        mode="bypassPermissions")
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "deny" and "a person's decision" in reason


def test_the_person_s_own_override_lets_the_record_write_through(scripts_path, project, monkeypatch, capsys):
    monkeypatch.setenv("MYCELIUM_GUARD_STATE_EDIT", "1")
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    call = _edit_record(project, TARGET_ONLY, COMMITTED + "  in_scope_paths: [app/billing/]\n")
    assert _run(scripts_path, monkeypatch, capsys, project, call) == (None, "")


def test_a_whole_record_written_at_once_is_judged_the_same(scripts_path, project, monkeypatch, capsys):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    call = {"tool_name": "Write", "permission_mode": "default",
            "tool_input": {"file_path": str(project / ".claude/diamonds/active.yml"),
                           "content": record(cycle(folders="[app/billing/]"))}}
    decision, reason = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "ask" and "app/billing/" in reason


def test_a_first_record_that_names_folders_asks(scripts_path, project, monkeypatch, capsys):
    call = {"tool_name": "Write", "permission_mode": "default",
            "tool_input": {"file_path": str(project / ".claude/diamonds/active.yml"),
                           "content": record(cycle(folders="[app/billing/]"))}}
    decision, _ = _run(scripts_path, monkeypatch, capsys, project, call)
    assert decision == "ask"


@pytest.mark.parametrize(("old", "new"), [
    ("a line that is not in the file", "anything"),
    ("active_diamonds:", "active_diamonds: [this is: not valid: yaml"),
])
def test_a_record_write_it_cannot_work_out_is_left_to_the_scale_lock(
        scripts_path, project, monkeypatch, capsys, old, new):
    _hold(project, record(cycle(decisions=TARGET_ONLY, folders=None)))
    assert _run(scripts_path, monkeypatch, capsys, project, _edit_record(project, old, new)) == (None, "")


# ---------------------------------------------------------------- what session start says


def test_notices_are_empty_when_there_is_nothing_to_say(scripts_path, project):
    sc = _import(scripts_path)
    assert sc.notices(str(project)) == ""
    _hold(project, record(cycle()))
    assert sc.notices(str(project)) == ""
    _hold(project, record(cycle(folders="[]")))
    assert sc.notices(str(project)) == ""


def test_notices_name_a_cycle_that_committed_with_nothing_said(scripts_path, project):
    _hold(project, record(cycle(folders=None), cycle(cid="l4-search", folders="[app/search/]")))
    said = _import(scripts_path).notices(str(project))
    assert "l4-billing" in said and "l4-search" not in said
    assert "not held to any folder" in said and "in_scope_paths: []" in said


def test_notices_say_an_old_state_file_is_no_longer_read(scripts_path, project):
    (project / ".claude/state/active-execution.json").write_text("{}")
    said = _import(scripts_path).notices(str(project))
    assert "is no longer read" in said and "product writes are refused" in said
    _hold(project, "active_diamonds: [not closed\n")
    assert "is no longer read" in _import(scripts_path).notices(str(project))


def test_the_notices_command_prints_them(scripts_path, project):
    _hold(project, record(cycle(folders=None)))
    done = subprocess.run([sys.executable, str(scripts_path / "scope_check.py"), "--notices",
                           str(project)], text=True, capture_output=True, check=False)
    assert done.returncode == 0 and "SCOPE HOLD" in done.stdout and "l4-billing" in done.stdout
