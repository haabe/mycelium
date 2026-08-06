"""Coverage tests for check_surface_registry.py — the right-content-wrong-surface mechanism.

The cluster (criterion met 2026-07-26): an artifact is produced correctly and
written to a surface no downstream mechanism reads. Three instances in three
different artifact pairs — BVSSH assessments, release lessons, upstream
candidates. The first two got point-checks; the criterion said a third instance
in a different pair graduates this to a GENERAL mechanism rather than a third
point-check.

The negative controls are the load-bearing tests here. A registry checker that
can only pass is the same class of defect as the checks this session spent the
day fixing: green over nothing. `test_false_wiring_claim_fails` and
`test_missing_reader_file_fails` exist so this one cannot join that family.
"""
import json
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_surface_registry

    return check_surface_registry


def _tree(root):
    """Build a repo-shaped tree: <root>/plugins/mycelium/{engine,hooks}."""
    plugin_root = root / "plugins" / "mycelium"
    (plugin_root / "engine").mkdir(parents=True, exist_ok=True)
    (plugin_root / "hooks").mkdir(parents=True, exist_ok=True)
    return plugin_root


def _registry(plugin_root, body):
    (plugin_root / "engine" / "surface-registry.yml").write_text(body)


def _reader(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _run(mod, *argv):
    old = sys.argv
    sys.argv = ["check_surface_registry", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


# --- negative controls: the tests that keep this from being green-over-nothing

def test_false_wiring_claim_fails(scripts_path, tmp_path, capsys):
    """A declared reader that never names its surface is a loop that cannot close."""
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: broken-claim
    authoritative_surface: ".claude/canvas/bvssh-health.yml"
    read_by: ["plugins/mycelium/hooks/liar.sh"]
""")
    _reader(tmp_path, "plugins/mycelium/hooks/liar.sh",
            "#!/bin/sh\necho 'I claim to read it but never name it'\n")

    assert _run(mod, "--plugin-root", str(plugin_root)) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "bvssh-health.yml" in out
    assert "cannot close" in out


def test_missing_reader_file_fails(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: ghost-reader
    authoritative_surface: ".claude/canvas/thing.yml"
    read_by: ["plugins/mycelium/hooks/does-not-exist.sh"]
""")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 1
    assert "does not exist" in capsys.readouterr().out


def test_honest_wiring_claim_passes(scripts_path, tmp_path):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: honest
    authoritative_surface: ".claude/canvas/bvssh-health.yml"
    read_by: ["plugins/mycelium/hooks/real.sh"]
""")
    _reader(tmp_path, "plugins/mycelium/hooks/real.sh",
            "#!/bin/sh\ncat .claude/canvas/bvssh-health.yml\n")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 0


# --- open rows are reported, never skipped ---------------------------------

def test_open_row_is_reported_not_skipped(scripts_path, tmp_path, capsys):
    """The registry's most important row is currently the one with no surface."""
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: upstream-candidate
    authoritative_surface: null
    read_by: []
""")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 0
    out = capsys.readouterr().out
    assert "OPEN" in out
    assert "upstream-candidate" in out


def test_surface_with_no_reader_is_open(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: unread
    authoritative_surface: ".claude/canvas/thing.yml"
    read_by: []
""")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 0
    assert "no reader" in capsys.readouterr().out


def test_strict_fails_on_open_rows(scripts_path, tmp_path):
    """--strict exists so a project that closed all its rows can keep them closed."""
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: upstream-candidate
    authoritative_surface: null
    read_by: []
""")
    assert _run(mod, "--plugin-root", str(plugin_root), "--strict") == 1


# --- absent-input discipline (anti-pattern #9) ------------------------------

def test_no_registry_is_a_precondition_failure_not_a_pass(scripts_path, tmp_path, capsys):
    """The registry ships with the plugin, so its absence means a broken tree.

    Originally exit 0 on the reasoning that not every project has a registry.
    check_empty_input_honesty.py rejected it, correctly: nothing was verified,
    so 0 is the one answer that is never true.
    """
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    assert _run(mod, "--plugin-root", str(plugin_root)) == 2
    assert "NOTHING WAS VERIFIED" in capsys.readouterr().err


def test_malformed_registry_fails_loud(scripts_path, tmp_path, capsys):
    """A malformed registry must never read as an empty one."""
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, "surfaces: [unclosed\n")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 2
    assert "ERROR" in capsys.readouterr().err


def test_surfaces_not_a_list_fails_loud(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, "schema_version: 1\nsurfaces: not-a-list\n")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 2
    assert "not a list" in capsys.readouterr().err


def test_empty_registry_says_so(scripts_path, tmp_path, capsys):
    """'No rows' and 'I could not find the rows' must differ."""
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, "schema_version: 1\n")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 0
    assert "registry-empty" in capsys.readouterr().out


def test_malformed_row_is_reported(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, "schema_version: 1\nsurfaces:\n  - just-a-string\n")
    assert _run(mod, "--plugin-root", str(plugin_root)) == 1
    assert "not a mapping" in capsys.readouterr().out


# --- interface + the shipped tree -------------------------------------------

def test_json_output(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    plugin_root = _tree(tmp_path)
    _registry(plugin_root, """
schema_version: 1
surfaces:
  - artifact_class: broken
    authoritative_surface: ".claude/canvas/x.yml"
    read_by: ["plugins/mycelium/hooks/liar.sh"]
""")
    _reader(tmp_path, "plugins/mycelium/hooks/liar.sh", "nothing relevant here\n")
    assert _run(mod, "--plugin-root", str(plugin_root), "--json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "broken"
    assert len(payload["findings"]) == 1


def test_bad_plugin_root_is_an_input_error(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    assert _run(mod, "--plugin-root", str(tmp_path / "nope")) == 2
    assert "not a directory" in capsys.readouterr().err


def test_shipped_registry_is_honest(scripts_path):
    """The live gate: the shipped tree must satisfy its own registry.

    Every wiring claim in the real surface-registry.yml is verified against the
    real reader files. This is the check that would have caught the BVSSH orphan
    class at the config layer.
    """
    mod = _import(scripts_path)
    plugin_root = scripts_path.parent
    repo_root = plugin_root.parent.parent
    findings, open_rows, checked = mod.evaluate(plugin_root, repo_root)
    assert findings == [], f"broken wiring claims in the shipped registry: {findings}"
    assert checked > 0, "the shipped registry verified zero readers — it is not doing anything"
    # The upstream-candidate row is knowingly open; assert it stays visible
    # rather than silently disappearing.
    assert any(o["artifact_class"] == "upstream-candidate" for o in open_rows)
