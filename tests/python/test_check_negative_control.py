"""Coverage proof for check_negative_control.py — the guard-must-bite guard.

This file has to satisfy the rule its subject enforces: the FIRST test below is
its own failure-direction assertion. If check_negative_control ever stopped
flagging a happy-path-only guard, this test fails.

Regression context: Check 37 asks "does every check have a test?" and never asks
whether that test would fail if the check broke. `verify_citations.py` shipped 14
green tests while its matcher matched 0% of real citations for ~2.5 months, and
the auto-dogfood battery scored 7/7 both with AND without the operating contract
injected. Both are tests whose verdict did not depend on their subject.

Three of this guard's own false positives were found by running it against the
real test corpus rather than trusting it: hyphen/underscore test names, hooks
whose sad path lives in a Python helper's test, and PreToolUse hooks that signal
refusal in the stdout payload rather than the exit code (test_scope_check.py's
own docstring: "both allow and deny exit 0"). Each is pinned below.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_negative_control

    return check_negative_control


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _guard(root, name, body="print('x')\n"):
    sub = "hooks" if name.endswith(".sh") else "scripts"
    _write(root / "plugins/mycelium" / sub / name, body)


# ---------------------------------------------------------------------------
# The failure direction — this guard's own negative control
# ---------------------------------------------------------------------------

def test_happy_path_only_test_is_flagged(scripts_path, tmp_path):
    """A guard whose test only asserts success is the whole point of this check."""
    mod = _import(scripts_path)
    _guard(tmp_path, "check_thing.py")
    _write(
        tmp_path / "tests/python/test_check_thing.py",
        "def test_ok(m):\n    assert m.scan(x) == []\n",
    )
    report = mod.scan(tmp_path)
    assert len(report["findings"]) == 1
    assert report["findings"][0]["guard"] == "check_thing.py"
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_guard_with_no_test_at_all_is_flagged(scripts_path, tmp_path):
    """No test file is a stronger version of the same gap."""
    mod = _import(scripts_path)
    _guard(tmp_path, "check_thing.py")
    findings = mod.scan(tmp_path)["findings"]
    assert len(findings) == 1
    assert "no test file found" in findings[0]["detail"]


# ---------------------------------------------------------------------------
# The pass direction, and the three false positives that were measured out
# ---------------------------------------------------------------------------

def test_exit_code_assertion_satisfies(scripts_path, tmp_path):
    """`main(...) == 1` is a failure-direction assertion."""
    mod = _import(scripts_path)
    _guard(tmp_path, "check_thing.py")
    _write(
        tmp_path / "tests/python/test_check_thing.py",
        'def test_bites(m):\n    assert m.main(["--root", "x"]) == 1\n',
    )
    assert mod.scan(tmp_path)["findings"] == []


def test_deny_payload_assertion_satisfies(scripts_path, tmp_path):
    """FALSE POSITIVE #3: PreToolUse hooks deny in the payload, exiting 0.

    Selecting tokens by the guard's extension checked this Python test with bash
    idioms and wrongly flagged a hook that does assert denial.
    """
    mod = _import(scripts_path)
    _guard(tmp_path, "scope-gate.sh", "exit 2\nhelper=scope_check.py\n")
    _write(
        tmp_path / "tests/python/test_scope_check.py",
        'def test_deny(m):\n'
        '    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"\n',
    )
    assert mod.scan(tmp_path)["findings"] == []


def test_helper_test_resolves_for_a_hook(scripts_path, tmp_path):
    """FALSE POSITIVE #2: a hook's sad path lives in its helper's test."""
    mod = _import(scripts_path)
    _guard(tmp_path, "scope-gate.sh", 'exit 2\npython3 "$H"/scope_check.py\n')
    _write(
        tmp_path / "tests/python/test_scope_check.py",
        "def test_deny(m):\n    assert m.main([]) == 1\n",
    )
    tests = mod._test_files_for("scope-gate.sh", tmp_path)
    assert any("test_scope_check.py" in str(t) for t in tests)


def test_hyphen_underscore_name_variants_resolve(scripts_path, tmp_path):
    """FALSE POSITIVE #1: hyphenated hook, underscored test filename."""
    mod = _import(scripts_path)
    _guard(tmp_path, "framework-guard.sh", "exit 2\n")
    _write(
        tmp_path / "tests/python/test_framework_guard.py",
        "def test_deny(m):\n    assert m.main([]) == 1\n",
    )
    assert mod.scan(tmp_path)["findings"] == []


# ---------------------------------------------------------------------------
# Scope derivation — advisory hooks are detected, not enumerated
# ---------------------------------------------------------------------------

def test_non_blocking_hook_is_derived_as_advisory(scripts_path, tmp_path):
    """A hook that cannot block has no failure direction to assert.

    Derived from the hook's source, not from a hand-maintained exempt list —
    adding a blocking construct immediately makes the guard owe a sad-path test,
    with no list to remember to update.
    """
    mod = _import(scripts_path)
    _guard(tmp_path, "post-write-nudge.sh", 'echo "just a nudge"\nexit 0\n')
    assert mod.scan(tmp_path)["findings"] == []


def test_adding_a_block_makes_the_same_hook_owe_a_test(scripts_path, tmp_path):
    """The other half of the derivation: gain teeth, gain the obligation."""
    mod = _import(scripts_path)
    _guard(tmp_path, "post-write-nudge.sh", "echo hi\nexit 2\n")
    findings = mod.scan(tmp_path)["findings"]
    assert len(findings) == 1, "a hook that can now block owes a sad-path test"


def test_stub_exemption_is_argued(scripts_path):
    """The one hand-exemption carries a stated reason, per Check 37's discipline."""
    mod = _import(scripts_path)
    assert "check_gated_by.py" in mod.EXEMPT
    assert "stub" in mod.EXEMPT["check_gated_by.py"].lower()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_json_output_is_parseable(scripts_path, tmp_path, capsys):
    import json

    mod = _import(scripts_path)
    _guard(tmp_path, "check_thing.py")
    rc = mod.main(["--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["findings"][0]["guard"] == "check_thing.py"


def test_missing_root_returns_2(scripts_path, tmp_path):
    mod = _import(scripts_path)
    assert mod.main(["--root", str(tmp_path / "nope")]) == 2


def test_real_repo_passes_its_own_rule(scripts_path):
    """The shipped tree must satisfy this guard — the live gate, not a fixture."""
    mod = _import(scripts_path)
    root = scripts_path.parents[2]
    findings = mod.scan(root)["findings"]
    assert findings == [], f"guards tested only passing: {findings}"
