"""Coverage tests for check_wiring.py — the never-reached-mechanism guard.

Each test below is a regression lock on a mechanism that shipped green and did
nothing, found in the 2026-07-26 silently-inert sweep:

  Rule A — `ingest_warnings.py` was documented "auto-updated from CI signals"
    and published as "Shipped (v0.16.0)" while being invoked by nothing; its
    only CI mention was a path-layout comment naming the file. So a caller found
    ONLY on a comment line must not count as wiring.
  Rule B — `/xai-check` read `${CLAUDE_PLUGIN_ROOT}/jit-tooling/active-stack.yml`,
    a path that never existed anywhere, so Theory Gate 13 could never fire
    (~2.5 months). And `scaffold-cost-check` read AGENTS.md through the plugin
    cache, where repo-root files are not packaged.
  Rule C — `warnings-log.md` was split three ways: setup created it under
    `harness/`, the writer resolved `memory/`, and /corrections-audit read both
    in different steps, so the Count-3+ graduation trigger read a file the writer
    never touched.

The guard must also stay quiet on the legitimate shapes, or it becomes noise
that gets ignored — which is how the original holes survived.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_wiring

    return check_wiring


def _write(p, text=""):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def _plugin(root):
    return root / "plugins/mycelium"


# ---------------------------------------------------------------------------
# Rule A — orphan scripts
# ---------------------------------------------------------------------------

def test_rule_a_script_with_no_caller_is_flagged(scripts_path, tmp_path):
    """A shipped script nothing invokes is one finding; exit 1."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/lonely.py", "print('hi')\n")
    findings = mod.check_orphan_scripts(tmp_path)
    assert len(findings) == 1
    assert findings[0]["rule"] == "A"
    assert "lonely.py" in findings[0]["target"]
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_rule_a_commented_out_caller_does_not_count(scripts_path, tmp_path):
    """THE ingest_warnings REGRESSION: a comment naming the script is not a caller."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/lonely.py", "print('hi')\n")
    _write(
        tmp_path / ".github/workflows/validate.yml",
        "jobs:\n  # runs lonely.py eventually\n  #   run: python3 lonely.py\n",
    )
    findings = mod.check_orphan_scripts(tmp_path)
    assert len(findings) == 1, "a commented-out invocation must not satisfy the check"


def test_rule_a_real_ci_caller_satisfies(scripts_path, tmp_path):
    """An uncommented CI invocation is wiring."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/wired.py", "print('hi')\n")
    _write(
        tmp_path / ".github/workflows/validate.yml",
        "jobs:\n  steps:\n    - run: python3 plugins/mycelium/scripts/wired.py --root .\n",
    )
    assert mod.check_orphan_scripts(tmp_path) == []


def test_rule_a_skill_caller_satisfies(scripts_path, tmp_path):
    """A SKILL.md that invokes the script is wiring (the validate_mermaid fix)."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/validate_mermaid.py", "print('hi')\n")
    _write(
        _plugin(tmp_path) / "skills/diamond-render/SKILL.md",
        "pipe it: python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.py -\n",
    )
    assert mod.check_orphan_scripts(tmp_path) == []


def test_rule_a_allowlisted_script_is_exempt(scripts_path, tmp_path):
    """A documented stub/template on the allowlist is not a finding."""
    mod = _import(scripts_path)
    name = next(iter(mod.ORPHAN_ALLOWLIST))
    _write(_plugin(tmp_path) / f"scripts/{name}", "# parked\n")
    assert mod.check_orphan_scripts(tmp_path) == []


def test_rule_a_no_scripts_dir_is_quiet(scripts_path, tmp_path):
    """A tree with no scripts/ dir yields nothing rather than raising."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "engine/x.md", "hi\n")
    assert mod.check_orphan_scripts(tmp_path) == []


# ---------------------------------------------------------------------------
# Rule B — ${CLAUDE_PLUGIN_ROOT} refs must resolve
# ---------------------------------------------------------------------------

def test_rule_b_unresolvable_plugin_root_ref_is_flagged(scripts_path, tmp_path):
    """THE xai-check REGRESSION: a plugin-root ref to a nonexistent file."""
    mod = _import(scripts_path)
    _write(
        _plugin(tmp_path) / "skills/xai-check/SKILL.md",
        "Read `${CLAUDE_PLUGIN_ROOT}/jit-tooling/active-stack.yml` first.\n",
    )
    findings = mod.check_plugin_root_refs(tmp_path)
    assert len(findings) == 1
    assert findings[0]["rule"] == "B"
    assert "active-stack.yml" in findings[0]["detail"]


def test_rule_b_repo_root_file_through_plugin_cache_is_flagged(scripts_path, tmp_path):
    """THE scaffold-cost-check REGRESSION: AGENTS.md is not packaged."""
    mod = _import(scripts_path)
    _write(tmp_path / "AGENTS.md", "router\n")  # exists at repo root...
    _write(
        _plugin(tmp_path) / "skills/scaffold-cost-check/SKILL.md",
        "- `${CLAUDE_PLUGIN_ROOT}/AGENTS.md` if present\n",
    )
    findings = mod.check_plugin_root_refs(tmp_path)
    assert len(findings) == 1, "...but resolving it through the plugin cache still fails"


def test_rule_b_resolvable_ref_is_quiet(scripts_path, tmp_path):
    """A plugin-root ref to a file that ships is fine."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "engine/theory-gates.md", "gates\n")
    _write(
        _plugin(tmp_path) / "skills/s/SKILL.md",
        "See `${CLAUDE_PLUGIN_ROOT}/engine/theory-gates.md`.\n",
    )
    assert mod.check_plugin_root_refs(tmp_path) == []


def test_rule_b_brace_alternation_expands(scripts_path, tmp_path):
    """`domains/{discovery|delivery}/CLAUDE.md` checks each branch."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "domains/discovery/CLAUDE.md", "d\n")
    _write(
        _plugin(tmp_path) / "engine/contract.md",
        "load `${CLAUDE_PLUGIN_ROOT}/domains/{discovery|delivery}/CLAUDE.md`\n",
    )
    findings = mod.check_plugin_root_refs(tmp_path)
    assert len(findings) == 1, "the missing delivery/ branch must be caught"
    assert "delivery" in findings[0]["detail"]


def test_rule_b_globs_and_placeholders_are_skipped(scripts_path, tmp_path):
    """`*` and `<name>` are patterns, not paths — no false positives."""
    mod = _import(scripts_path)
    _write(
        _plugin(tmp_path) / "engine/x.md",
        "`${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md` and `${CLAUDE_PLUGIN_ROOT}/s/<name>.md`\n",
    )
    assert mod.check_plugin_root_refs(tmp_path) == []


# ---------------------------------------------------------------------------
# Rule C — one canonical path per state file
# ---------------------------------------------------------------------------

def test_rule_c_split_state_path_is_flagged(scripts_path, tmp_path):
    """THE warnings-log REGRESSION: harness/ where the writer uses memory/."""
    mod = _import(scripts_path)
    _write(
        _plugin(tmp_path) / "skills/corrections-audit/SKILL.md",
        "read `.claude/harness/warnings-log.md` for open classes\n",
    )
    findings = mod.check_state_path_agreement(tmp_path)
    assert len(findings) == 1
    assert findings[0]["rule"] == "C"
    assert ".claude/memory/warnings-log.md" in findings[0]["detail"]


def test_rule_c_canonical_path_is_quiet(scripts_path, tmp_path):
    """The canonical path produces no finding."""
    mod = _import(scripts_path)
    _write(
        _plugin(tmp_path) / "skills/corrections-audit/SKILL.md",
        "read `.claude/memory/warnings-log.md` for open classes\n",
    )
    assert mod.check_state_path_agreement(tmp_path) == []


def test_rule_c_allowlisted_migration_doc_is_exempt(scripts_path, tmp_path):
    """migrate-from-legacy names the OLD path as its subject; that is not drift."""
    mod = _import(scripts_path)
    _write(
        _plugin(tmp_path) / "skills/migrate-from-legacy/SKILL.md",
        "preserve `.claude/harness/warnings-log.md` before pruning\n",
    )
    assert mod.check_state_path_agreement(tmp_path) == []


def test_rule_c_unregistered_file_is_ignored(scripts_path, tmp_path):
    """Only registered state files are policed — no blanket path opinions."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "engine/x.md", "see `.claude/whatever/random.md`\n")
    assert mod.check_state_path_agreement(tmp_path) == []


# ---------------------------------------------------------------------------
# Integration / CLI
# ---------------------------------------------------------------------------

def test_clean_tree_exits_zero(scripts_path, tmp_path):
    """A tree with no breaks exits 0."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "engine/x.md", "nothing to see\n")
    assert mod.scan(tmp_path)["findings"] == []
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_json_output_is_parseable(scripts_path, tmp_path, capsys):
    """--json emits valid JSON carrying the findings."""
    import json

    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/lonely.py", "x\n")
    rc = mod.main(["--root", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["findings"][0]["rule"] == "A"


def test_missing_root_returns_2(scripts_path, tmp_path):
    """A nonexistent --root is a setup error, not a silent pass."""
    mod = _import(scripts_path)
    assert mod.main(["--root", str(tmp_path / "nope")]) == 2


def test_self_exempt_covers_only_this_checker(scripts_path):
    """The self-exemption is one file, so a sibling checker's dead ref still fails."""
    mod = _import(scripts_path)
    assert {"plugins/mycelium/scripts/check_wiring.py"} == mod.SELF_EXEMPT


def test_real_repo_is_wired(scripts_path):
    """The shipped tree must satisfy its own guard (the live gate, not a fixture)."""
    mod = _import(scripts_path)
    root = scripts_path.parents[2]
    findings = mod.scan(root)["findings"]
    assert findings == [], f"wiring breaks in the shipped tree: {findings}"


# ---------------------------------------------------------------------------
# Rule D — an automation claim in prose is a promise the wiring must keep
# ---------------------------------------------------------------------------

def test_rule_d_claim_about_uncalled_script_is_flagged(scripts_path, tmp_path):
    """THE ingest_warnings REGRESSION from the documentation side."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/ingest_warnings.py", "x\n")
    _write(
        _plugin(tmp_path) / "engine/warning-handbook.md",
        "warnings-log.md is auto-updated by `ingest_warnings.py` from CI signals.\n",
    )
    findings = mod.check_automation_claims(tmp_path)
    assert len(findings) == 1
    assert findings[0]["rule"] == "D"
    assert "ingest_warnings.py" in findings[0]["detail"]


def test_rule_d_shipped_vx_claim_is_flagged(scripts_path, tmp_path):
    """The receipts-index form: "Shipped (v0.16.0)" beside an uncalled script."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/ingest_warnings.py", "x\n")
    _write(
        tmp_path / "docs/receipts/README.md",
        "| `ingest_warnings.py` + handbook | case | Shipped (v0.16.0) |\n",
    )
    findings = mod.check_automation_claims(tmp_path)
    assert len(findings) == 1, "a receipts-index 'Shipped' claim is still a claim"


def test_rule_d_claim_about_wired_script_is_quiet(scripts_path, tmp_path):
    """Once the script has a real caller, the same claim is true and passes."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/ingest_warnings.py", "x\n")
    _write(
        _plugin(tmp_path) / "engine/warning-handbook.md",
        "warnings-log.md is auto-updated by `ingest_warnings.py` from CI signals.\n",
    )
    _write(
        tmp_path / ".github/workflows/validate.yml",
        "    - run: python3 plugins/mycelium/scripts/ingest_warnings.py --dry-run\n",
    )
    assert mod.check_automation_claims(tmp_path) == []


def test_rule_d_changelog_narration_is_allowlisted(scripts_path, tmp_path):
    """A changelog records what once shipped; that is history, not a live promise."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/ingest_warnings.py", "x\n")
    _write(
        tmp_path / "docs/changelog.md",
        "v0.16.0 — `ingest_warnings.py` auto-updated the warnings log.\n",
    )
    assert mod.check_automation_claims(tmp_path) == []


def test_rule_d_unrelated_script_name_is_ignored(scripts_path, tmp_path):
    """A claim naming a script that does not ship is not this repo's problem."""
    mod = _import(scripts_path)
    _write(_plugin(tmp_path) / "scripts/real.py", "x\n")
    _write(
        _plugin(tmp_path) / "engine/x.md",
        "our data is auto-updated by `someone_elses_tool.py` nightly.\n",
    )
    assert mod.check_automation_claims(tmp_path) == []
