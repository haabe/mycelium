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
    import check_theory_fidelity  # noqa: PLC0415

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
