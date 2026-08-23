"""Coverage tests for check_theory_fidelity.py — the structural theory-mapping guard.

Locks in the structural-drift classes the guard exists to catch (so they fail CI
at write-time rather than at the next /theory-fidelity audit):
  A. a theories.md skill reference that no longer resolves,
  B. a `gate N` reference with no matching gate,
  C. an engine/harness doc-path reference that doesn't exist,
  D. a gate shipped without a `**Source**:` theory line,
  E. a name-only theory in a load-bearing tier (no mechanism pointer),
and confirms Tier-3 citation-only entries are exempt.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import check_theory_fidelity

    return check_theory_fidelity


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


CLEAN_THEORIES = """# Theories integrated

## Tier 1 — Load-bearing theories

### Foo — Author
Faithful prose. Implemented as: `/alpha`, gate 1.

## Tier 2 — Integrated theories

| Theory | Author(s) | Implemented as |
|---|---|---|
| Bar | Auth | `/beta` skill + `canvas/bar.yml` |
| Qux | Auth | rationale in `philosophy.md`; enforced via G-M2 |

## Tier 3 — Background theories

- **Baz** — citation only, informs ethics. No mechanism by design.

## See also
- nothing
"""

CLEAN_GATES = """# Theory Gates

### 1. Evidence Gate
**Source**: Sinek
Pass criteria: evidence present.
"""


def _setup(tmp_path, theories=CLEAN_THEORIES, gates=CLEAN_GATES, skills=("alpha", "beta")):
    _write(tmp_path / "docs/theories.md", theories)
    _write(tmp_path / "plugins/mycelium/engine/theory-gates.md", gates)
    _write(tmp_path / "plugins/mycelium/engine/philosophy_placeholder.md", "x")
    for s in skills:
        _write(tmp_path / f"plugins/mycelium/skills/{s}/SKILL.md", f"name: {s}")
    # philosophy.md is referenced by the Qux row (filename token only — presence,
    # not resolution, so it need not exist for E; create docs dir already done).
    return tmp_path


def test_clean_repo_is_green(scripts_path, tmp_path):
    mod = _import(scripts_path)
    _setup(tmp_path)
    report = mod.scan(tmp_path)
    assert report["errors"] == []
    assert report["gates_checked"] == 1
    assert mod.main(["--root", str(tmp_path)]) == 0


def test_phantom_skill_reference_flagged(scripts_path, tmp_path):
    """A: theories.md references /ghost but no such skill dir."""
    mod = _import(scripts_path)
    theories = CLEAN_THEORIES.replace("`/alpha`", "`/ghost`")
    _setup(tmp_path, theories=theories)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "A:skill-ref" and "ghost" in d for c, d in errs)
    assert mod.main(["--root", str(tmp_path)]) == 1


def test_phantom_gate_reference_flagged(scripts_path, tmp_path):
    """B: theories.md references gate 99 which doesn't exist."""
    mod = _import(scripts_path)
    theories = CLEAN_THEORIES.replace("gate 1", "gate 99")
    _setup(tmp_path, theories=theories)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "B:gate-ref" and "99" in d for c, d in errs)


def test_phantom_engine_path_flagged(scripts_path, tmp_path):
    """C: an engine/<file>.md reference that doesn't resolve."""
    mod = _import(scripts_path)
    theories = CLEAN_THEORIES.replace("`canvas/bar.yml`", "`engine/missing-doc.md`")
    _setup(tmp_path, theories=theories)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "C:doc-path" and "missing-doc.md" in d for c, d in errs)


def test_gate_without_source_flagged(scripts_path, tmp_path):
    """D: a gate section with no **Source**: line."""
    mod = _import(scripts_path)
    gates = "# Theory Gates\n\n### 1. Evidence Gate\nPass criteria only, no source.\n"
    _setup(tmp_path, gates=gates)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "D:gate-source" for c, d in errs)


def test_name_only_tier2_theory_flagged(scripts_path, tmp_path):
    """E: a Tier-2 row that is pure prose with no mechanism pointer."""
    mod = _import(scripts_path)
    theories = CLEAN_THEORIES.replace(
        "| Qux | Auth | rationale in `philosophy.md`; enforced via G-M2 |",
        "| Qux | Auth | a wonderful theory we deeply believe in |",
    )
    _setup(tmp_path, theories=theories)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "E:name-only" and "Qux" in d for c, d in errs)


def test_name_only_tier1_theory_flagged(scripts_path, tmp_path):
    """E: a Tier-1 section with no mechanism pointer."""
    mod = _import(scripts_path)
    theories = CLEAN_THEORIES.replace(
        "Faithful prose. Implemented as: `/alpha`, gate 1.",
        "Faithful prose with no concrete artifact named at all.",
    )
    _setup(tmp_path, theories=theories)
    errs = mod.scan(tmp_path)["errors"]
    assert any(c == "E:name-only" and "Foo" in d for c, d in errs)


def test_tier3_citation_only_is_exempt(scripts_path, tmp_path):
    """Tier-3 'Baz' has no mechanism and must NOT be flagged (citation-only by design)."""
    mod = _import(scripts_path)
    _setup(tmp_path)
    errs = mod.scan(tmp_path)["errors"]
    assert not any("Baz" in d for c, d in errs)


def test_missing_theories_file_is_setup_error(scripts_path, tmp_path):
    """Exit 2 when theories.md is absent."""
    mod = _import(scripts_path)
    _write(tmp_path / "plugins/mycelium/engine/theory-gates.md", CLEAN_GATES)
    assert mod.main(["--root", str(tmp_path)]) == 2


def test_json_output_runs(scripts_path, tmp_path, capsys):
    """--json path executes and emits parseable JSON."""
    import json

    mod = _import(scripts_path)
    _setup(tmp_path)
    rc = mod.main(["--root", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "errors" in parsed and rc == 0


# --- root auto-detect across layouts (v0.108.0) -----------------------------

def test_autodetect_finds_the_framework_tree_by_artifact(scripts_path, tmp_path):
    """Layout-agnostic: locate the theory surface, do not count parent directories.

    The upstream checkout puts this script at <root>/plugins/mycelium/scripts/; the
    installed plugin cache puts it at <cache>/<marketplace>/<plugin>/<version>/scripts/.
    The old `parents[3]` got the first right and the second silently wrong — every
    consumer-side run died with "missing docs/theories.md under
    ~/.claude/plugins/cache/haabe-mycelium".
    """
    import shutil
    mod = _import(scripts_path)

    cache = tmp_path / "cache/haabe-mycelium/mycelium/0.108.0/scripts"
    cache.mkdir(parents=True)
    shutil.copy(scripts_path / "check_theory_fidelity.py", cache)

    # No docs/theories.md anywhere above it — the real plugin-cache situation.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "tf_cached", cache / "check_theory_fidelity.py"
    )
    cached = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cached)
    assert cached._autodetect_root() is None

    # And the real upstream tree resolves to the repo root, not to a parent count.
    found = mod._autodetect_root()
    assert found is not None
    assert (found / mod.THEORIES_MD).is_file()


def test_no_framework_tree_is_na_not_an_error(scripts_path, tmp_path, capsys):
    """A consumer can do nothing about a missing framework artifact. N/A is honest;
    a path error at exit 2 is a false alarm, and false alarms are how a check gets
    ignored."""
    import importlib.util
    cache = tmp_path / "cache/mkt/plugin/1.0.0/scripts"
    cache.mkdir(parents=True)
    import shutil
    shutil.copy(scripts_path / "check_theory_fidelity.py", cache)
    spec = importlib.util.spec_from_file_location(
        "tf_na", cache / "check_theory_fidelity.py"
    )
    cached = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cached)

    assert cached.main([]) == 0
    assert "N/A" in capsys.readouterr().out


# --- consumer-repo N/A, and the teeth that must survive it ------------------------
# THE DEFECT (fixed v0.120.4). The honest N/A branch fired only when auto-detect
# returned None, so passing --root explicitly — which is exactly what
# /mycelium:framework-health instructs — skipped it and fell through to a path error.
# FOUR consecutive assessments (2026-08-08 .. 2026-08-23) reported this guard failing
# in a repo that has nothing it audits and can do nothing about it. The guard's own
# comment already said exiting 2 with a path error is dishonest for a consumer; the
# code said otherwise whenever a root was named.
def test_consumer_tree_is_na_not_an_error(tmp_path, scripts_path, capsys):
    """A plugin consumer has no theory surface and can do nothing about it."""
    mod = _import(scripts_path)
    (tmp_path / ".claude" / "canvas").mkdir(parents=True)  # a project, not the framework
    rc = mod.main(["--root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "N/A" in out
    assert "not the framework repo" in out


def test_framework_tree_missing_its_theory_surface_still_fails(tmp_path, scripts_path, capsys):
    """The teeth. N/A must not become a way for the framework to skip its own audit."""
    mod = _import(scripts_path)
    (tmp_path / "plugins" / "mycelium").mkdir(parents=True)  # IS the framework tree
    rc = mod.main(["--root", str(tmp_path)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "missing" in err
    assert "IS a framework tree" in err
