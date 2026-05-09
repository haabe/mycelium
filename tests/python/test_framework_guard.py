"""Unit tests for framework_guard.py — both file-path and Bash command paths."""
import json
import subprocess
import sys


def _import_guard(scripts_path):
    """Import framework_guard via sys.path (not packaged)."""
    sys.path.insert(0, str(scripts_path))
    import framework_guard  # noqa: PLC0415
    return framework_guard


def _run_guard(scripts_path, state_file, project_dir, tool_name, payload):
    """Invoke framework_guard.py as the hook would. Returns (allow|deny, message).

    `payload` shape varies by tool:
      - Bash: command string
      - Edit/Write/MultiEdit: file path → wrapped as {file_path: ...}
      - mcp__filesystem__write_file/edit_file: file path → wrapped as {path: ...}
      - mcp__filesystem__move_file: dict {source, destination}
    """
    if tool_name == "Bash":
        tool_input = {"command": payload}
    elif tool_name in ("mcp__filesystem__write_file", "mcp__filesystem__edit_file"):
        tool_input = {"path": payload}
    elif tool_name == "mcp__filesystem__move_file":
        tool_input = payload  # caller passes {source, destination}
    else:
        tool_input = {"file_path": payload}
    input_json = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    r = subprocess.run(
        ["python3", str(scripts_path / "framework_guard.py"),
         str(state_file), str(project_dir)],
        input=input_json, capture_output=True, text=True, check=False,
    )
    if r.stdout:
        return "deny", r.stdout
    return "allow", ""


# ============================================================
# is_framework() — file-path classification
# ============================================================

class TestIsFramework:
    def test_top_level_file_classified(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, rule = guard.is_framework(
            project_dir / "AGENTS.md", project_dir, framework,
        )
        assert matched
        assert "framework.top_level" in rule

    def test_directory_match_classified(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, rule = guard.is_framework(
            project_dir / ".claude" / "skills" / "foo" / "SKILL.md",
            project_dir, framework,
        )
        assert matched
        assert "framework.directories" in rule

    def test_project_state_not_classified(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, rule = guard.is_framework(
            project_dir / ".claude" / "canvas" / "purpose.yml",
            project_dir, framework,
        )
        assert not matched
        assert rule is None

    def test_outside_project_not_classified(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _ = guard.is_framework(
            "/tmp/some-other-place/AGENTS.md", project_dir, framework,
        )
        assert not matched

    def test_harness_file_classified(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, rule = guard.is_framework(
            project_dir / ".claude" / "harness" / "guardrails.md",
            project_dir, framework,
        )
        assert matched
        assert "harness_framework" in rule


# ============================================================
# is_framework_write_in_command() — Bash command analysis
# ============================================================

class TestBashWriteDetection:
    def test_cp_to_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "cp file.txt .claude/skills/foo/SKILL.md", project_dir, framework,
        )
        assert matched
        assert op == "copy/move/install/link"

    def test_redirect_to_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "echo bar > .claude/manifest.yml", project_dir, framework,
        )
        assert matched
        assert op == "redirect"

    def test_heredoc_to_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "cat > AGENTS.md << EOF\nfoo\nEOF", project_dir, framework,
        )
        assert matched
        assert op == "redirect"

    def test_tee_to_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "echo bar | tee .claude/harness/guardrails.md", project_dir, framework,
        )
        assert matched
        assert op == "tee"

    def test_sed_inplace_to_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "sed -i 's/foo/bar/' .claude/scripts/upgrade.sh", project_dir, framework,
        )
        assert matched
        assert op == "sed -i"

    def test_rm_framework_denied(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, op = guard.is_framework_write_in_command(
            "rm .claude/skills/interview/SKILL.md", project_dir, framework,
        )
        assert matched
        assert op == "rm"

    def test_cp_to_project_state_allowed(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cp file.txt .claude/canvas/purpose.yml", project_dir, framework,
        )
        assert not matched

    def test_redirect_to_project_state_allowed(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "echo foo > .claude/memory/scratch.md", project_dir, framework,
        )
        assert not matched

    def test_read_framework_allowed(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cat .claude/skills/interview/SKILL.md", project_dir, framework,
        )
        assert not matched

    def test_grep_framework_allowed(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "grep foo .claude/manifest.yml", project_dir, framework,
        )
        assert not matched

    def test_git_checkout_framework_allowlisted(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "git checkout .claude/skills/interview/SKILL.md", project_dir, framework,
        )
        assert not matched

    def test_upgrade_sh_allowlisted(self, project_dir, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "bash .claude/scripts/upgrade.sh", project_dir, framework,
        )
        assert not matched

    def test_substring_only_no_boundary_allowed(self, project_dir, manifest_path, scripts_path):
        """REGRESSION: framework path appearing only as path-suffix shouldn't match.

        e.g., '/tmp/foo/dot-claude/manifest.yml' contains '.claude/manifest.yml' but
        only as a suffix of a longer path — no token boundary precedes it.
        """
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cp /tmp/x /tmp/foo/dot-claude/manifest.yml", project_dir, framework,
        )
        assert not matched

    def test_known_limitation_cp_from_framework(self, project_dir, manifest_path, scripts_path):
        """KNOWN LIMITATION: cp/mv source/destination ambiguity (documented in fn).

        The heuristic can't distinguish src from dest — so cp FROM a framework
        path triggers DENY. Workaround is the active:false bypass. This test
        pins the current behavior so future refactor knows it's intentional.
        """
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cp .claude/manifest.yml /tmp/myc/x.yml", project_dir, framework,
        )
        assert matched, "Known limitation: heuristic can't tell src from dest"


# ============================================================
# main() — end-to-end via subprocess
# ============================================================

class TestMainDispatch:
    def test_edit_framework_file_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "Edit", str(project_dir / ".claude" / "skills" / "foo" / "SKILL.md"),
        )
        assert verdict == "deny"
        assert "framework.directories" in msg

    def test_edit_project_state_allows(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "Edit", str(project_dir / ".claude" / "canvas" / "purpose.yml"),
        )
        assert verdict == "allow"

    def test_bash_cp_to_framework_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "Bash", "cp file.txt .claude/skills/foo/SKILL.md",
        )
        assert verdict == "deny"
        assert "Mycelium framework-guard" in msg

    def test_bash_read_allows(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "Bash", "cat .claude/skills/interview/SKILL.md",
        )
        assert verdict == "allow"

    def test_active_false_disables_guard(self, project_dir, manifest_path, scripts_path):
        """When upstream.json has active:false, guard is silent regardless of target."""
        state_file = project_dir / ".claude" / "state" / "upstream.json"
        state_file.write_text(json.dumps({"upstream_repo": "/x", "active": False}))
        verdict, _ = _run_guard(
            scripts_path, state_file, project_dir,
            "Edit", str(project_dir / ".claude" / "skills" / "foo" / "SKILL.md"),
        )
        assert verdict == "allow"

    def test_no_state_file_disables_guard(self, project_dir, manifest_path, scripts_path):
        """When upstream.json doesn't exist, guard is silent (default for non-dogfood projects)."""
        verdict, _ = _run_guard(
            scripts_path, project_dir / ".claude" / "state" / "nonexistent.json",
            project_dir,
            "Edit", str(project_dir / ".claude" / "skills" / "foo" / "SKILL.md"),
        )
        assert verdict == "allow"

    def test_unknown_tool_silently_passes(self, project_dir, manifest_path, upstream_state, scripts_path):
        """Tools other than Edit/Write/MultiEdit/Bash/mcp__filesystem__* are not classified."""
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "Read", str(project_dir / "AGENTS.md"),
        )
        assert verdict == "allow"

    # ============================================================
    # MCP filesystem coverage (added 2026-05-09 — F6 follow-up).
    # Closes the bypass surfaced during the team-topologies dogfood
    # where mcp__filesystem__move_file cleanly evaded the guard
    # because matchers only listed Anthropic-built tools.
    # ============================================================

    def test_mcp_filesystem_write_to_framework_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__write_file",
            str(project_dir / ".claude" / "skills" / "foo" / "SKILL.md"),
        )
        assert verdict == "deny"
        assert "framework.directories" in msg

    def test_mcp_filesystem_write_to_project_state_allows(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__write_file",
            str(project_dir / ".claude" / "canvas" / "purpose.yml"),
        )
        assert verdict == "allow"

    def test_mcp_filesystem_edit_to_framework_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__edit_file",
            str(project_dir / "AGENTS.md"),
        )
        assert verdict == "deny"
        assert "framework.top_level" in msg

    def test_mcp_filesystem_move_into_framework_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        """Move INTO framework path = framework write."""
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__move_file",
            {
                "source": str(project_dir / ".claude" / "canvas" / "purpose.yml"),
                "destination": str(project_dir / "AGENTS.md"),
            },
        )
        assert verdict == "deny"
        # destination is framework — should match top_level
        assert "AGENTS.md" in msg or "framework.top_level" in msg

    def test_mcp_filesystem_move_out_of_framework_denies(self, project_dir, manifest_path, upstream_state, scripts_path):
        """Move OUT of framework path = framework deletion (also forbidden)."""
        verdict, msg = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__move_file",
            {
                "source": str(project_dir / "AGENTS.md"),
                "destination": str(project_dir / ".claude" / "canvas" / "stolen.md"),
            },
        )
        assert verdict == "deny"
        assert "AGENTS.md" in msg or "framework.top_level" in msg

    def test_mcp_filesystem_move_within_project_state_allows(self, project_dir, manifest_path, upstream_state, scripts_path):
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__move_file",
            {
                "source": str(project_dir / ".claude" / "canvas" / "a.yml"),
                "destination": str(project_dir / ".claude" / "canvas" / "b.yml"),
            },
        )
        assert verdict == "allow"

    def test_mcp_filesystem_write_no_path_fails_open(self, project_dir, manifest_path, upstream_state, scripts_path):
        """Empty path → fail open (consistent with Edit handler behavior)."""
        verdict, _ = _run_guard(
            scripts_path, upstream_state, project_dir,
            "mcp__filesystem__write_file", "",
        )
        assert verdict == "allow"


# ============================================================
# Internal helper unit tests (raise framework_guard coverage)
# ============================================================

class TestInternalHelpers:
    def test_extract_framework_paths_includes_all_buckets(self, manifest_path, scripts_path):
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        paths = guard._extract_framework_paths(framework)
        assert "AGENTS.md" in paths  # top_level
        assert ".claude/skills/" in paths  # directories
        assert ".claude/manifest.yml" in paths  # single_files
        assert ".claude/harness/guardrails.md" in paths  # harness_framework
        assert ".claude/canvas/README.md" in paths  # preserved_dir_readmes
        assert ".claude/evals/scenarios/" in paths  # evals_replace
        assert ".claude/jit-tooling/metrics-adapters/github.md" in paths

    def test_path_appears_at_boundary_start_of_string(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert guard._path_appears_at_boundary("AGENTS.md is here", "AGENTS.md")

    def test_path_appears_at_boundary_after_space(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert guard._path_appears_at_boundary("cp x AGENTS.md", "AGENTS.md")

    def test_path_appears_at_boundary_after_quote(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert guard._path_appears_at_boundary('cp x "AGENTS.md"', "AGENTS.md")

    def test_path_not_at_boundary_inside_longer_path(self, scripts_path):
        """Substring false-positive guard."""
        guard = _import_guard(scripts_path)
        assert not guard._path_appears_at_boundary("/tmp/foo/AGENTS.md", "AGENTS.md")

    def test_is_command_allowlisted_upgrade(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert guard._is_command_allowlisted("bash .claude/scripts/upgrade.sh")
        assert guard._is_command_allowlisted("bash ./.claude/scripts/upgrade.sh")

    def test_is_command_allowlisted_git(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert guard._is_command_allowlisted("git status")
        assert guard._is_command_allowlisted("git checkout main")
        assert guard._is_command_allowlisted("git push origin main")
        assert guard._is_command_allowlisted("git rm --cached file.txt")
        assert guard._is_command_allowlisted("git mv old.txt new.txt")

    def test_is_command_allowlisted_git_with_global_opts(self, scripts_path):
        """git -C /path / git --no-pager / git -c key=val should match too."""
        guard = _import_guard(scripts_path)
        assert guard._is_command_allowlisted("git -C /tmp/repo rm --cached foo")
        assert guard._is_command_allowlisted("git -c user.name=foo commit -m x")
        assert guard._is_command_allowlisted("git --no-pager log")
        assert guard._is_command_allowlisted("git --git-dir=/tmp/x.git status")

    def test_is_segment_allowlisted_per_segment(self, scripts_path):
        """Per-segment allowlist: compound commands check each segment separately."""
        guard = _import_guard(scripts_path)
        # The whole command starts with `cd` (not allowlisted), but the second
        # segment is `git rm` (allowlisted) — _is_segment_allowlisted returns
        # True for the git segment when called per-segment by the scanner.
        assert guard._is_segment_allowlisted("git rm --cached .claude/skills/foo")
        assert not guard._is_segment_allowlisted("cd /tmp/somewhere")

    def test_is_command_not_allowlisted_random(self, scripts_path):
        guard = _import_guard(scripts_path)
        assert not guard._is_command_allowlisted("rm -rf /")
        assert not guard._is_command_allowlisted("cp x y")

    def test_compound_commands_split_correctly(self, project_dir, manifest_path, scripts_path):
        """Per-segment scan should catch a write hidden in a compound command."""
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        # Read first, then write to framework — hook should still catch the write
        matched, _, _ = guard.is_framework_write_in_command(
            "cat foo.txt && echo bar > .claude/manifest.yml",
            project_dir, framework,
        )
        assert matched

    def test_compound_with_allowlisted_git_segment_passes(self, project_dir, manifest_path, scripts_path):
        """REGRESSION: `cd /path && git rm framework_file` was previously denied
        because the whole-command allowlist didn't match (started with `cd`).
        The per-segment allowlist fix makes the git rm segment recognized as
        safe even in compound commands. Closes follow-up #2 from the L4
        cleanup cycle (cycle-001).
        """
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cd /tmp/somewhere && git rm --cached .claude/skills/foo/SKILL.md",
            project_dir, framework,
        )
        assert not matched, "git rm in compound command should be allowlisted per-segment"

    def test_compound_with_allowlisted_upgrade_segment_passes(self, project_dir, manifest_path, scripts_path):
        """Compound that includes `bash .claude/scripts/upgrade.sh` should pass."""
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "cd /tmp && bash .claude/scripts/upgrade.sh && echo done",
            project_dir, framework,
        )
        assert not matched

    def test_compound_unsafe_segment_still_caught(self, project_dir, manifest_path, scripts_path):
        """Per-segment allowlist must NOT mask a real unsafe write in another segment."""
        guard = _import_guard(scripts_path)
        framework = guard.parse_manifest(manifest_path)
        matched, _, _ = guard.is_framework_write_in_command(
            "git status && echo bar > .claude/manifest.yml",
            project_dir, framework,
        )
        assert matched, "Unsafe write segment must still be caught even when sibling segments are safe"

    def test_load_state_returns_none_for_missing(self, project_dir, scripts_path):
        guard = _import_guard(scripts_path)
        state = guard._load_state(project_dir / "nonexistent.json")
        assert state is None

    def test_load_state_returns_none_for_inactive(self, project_dir, scripts_path):
        guard = _import_guard(scripts_path)
        state_file = project_dir / "inactive.json"
        state_file.write_text(json.dumps({"upstream_repo": "/x", "active": False}))
        state = guard._load_state(state_file)
        assert state is None

    def test_load_state_returns_dict_for_active(self, project_dir, scripts_path):
        guard = _import_guard(scripts_path)
        state_file = project_dir / "active.json"
        state_file.write_text(json.dumps({"upstream_repo": "/x", "active": True}))
        state = guard._load_state(state_file)
        assert state is not None
        assert state["upstream_repo"] == "/x"


class TestDenyHelpers:
    """Test the deny-message formatting (sys.exit'd by deny() — capture via SystemExit)."""

    def test_deny_emits_json_to_stdout(self, scripts_path, capsys):
        guard = _import_guard(scripts_path)
        try:
            guard.deny("test reason")
        except SystemExit as e:
            assert e.code == 0
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "test reason"
        assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"

    def test_deny_file_edit_message_includes_rule_and_upstream(self, scripts_path, capsys):
        guard = _import_guard(scripts_path)
        try:
            guard._deny_file_edit("AGENTS.md", "framework.top_level: AGENTS.md", "/path/upstream")
        except SystemExit:
            pass
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        msg = out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "AGENTS.md" in msg
        assert "framework.top_level" in msg
        assert "/path/upstream" in msg
        assert "active" in msg  # bypass instructions present

    def test_deny_bash_write_message_includes_path_op_upstream(self, scripts_path, capsys):
        guard = _import_guard(scripts_path)
        try:
            guard._deny_bash_write("AGENTS.md", "redirect", "/path/upstream")
        except SystemExit:
            pass
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        msg = out["hookSpecificOutput"]["permissionDecisionReason"]
        assert "AGENTS.md" in msg
        assert "redirect" in msg
        assert "/path/upstream" in msg
        assert "Bash coverage gap" in msg  # cross-references the original gap
