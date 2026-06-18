"""Coverage tests for validate_mermaid.py — the static render-fleet validator.

The script does two deterministic checks the agent cannot do by eye:
  1. state-ID consistency (F11): transition/class targets must reference a
     declared `state "..." as <ID>` (or a `ID : label` decl, or `[*]`).
  2. WCAG AA contrast (F13): label-on-base themeVariable colour pairs must
     meet 4.5:1.
Plus extraction of the fenced ```mermaid block and the CLI fail-open path.
"""
import sys


def _import(scripts_path):
    sys.path.insert(0, str(scripts_path))
    import validate_mermaid  # noqa: PLC0415

    return validate_mermaid


# ---------------------------------------------------------------------------
# extract_mermaid
# ---------------------------------------------------------------------------

def test_extract_pulls_fenced_block(scripts_path):
    mod = _import(scripts_path)
    text = "intro\n```mermaid\nstateDiagram-v2\n  A --> B\n```\noutro"
    out = mod.extract_mermaid(text)
    assert "stateDiagram-v2" in out
    assert "intro" not in out
    assert "outro" not in out


def test_extract_falls_back_to_whole_text(scripts_path):
    mod = _import(scripts_path)
    text = "stateDiagram-v2\n  A --> B"
    assert mod.extract_mermaid(text) == text


# ---------------------------------------------------------------------------
# contrast math
# ---------------------------------------------------------------------------

def test_contrast_ratio_black_on_white_is_max(scripts_path):
    mod = _import(scripts_path)
    ratio = mod.contrast_ratio("#000000", "#ffffff")
    assert round(ratio, 1) == 21.0


def test_contrast_ratio_identical_is_one(scripts_path):
    mod = _import(scripts_path)
    assert round(mod.contrast_ratio("#808080", "#808080"), 2) == 1.0


# ---------------------------------------------------------------------------
# check_contrast
# ---------------------------------------------------------------------------

def test_contrast_pass_high_contrast_pair(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "init:\n"
        "  themeVariables:\n"
        "    'cScale4': '#000000'\n"
        "    'cScaleLabel4': '#ffffff'\n"
    )
    fails, passes = mod.check_contrast(diagram)
    assert fails == []
    assert passes == 1


def test_contrast_fail_low_contrast_pair(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "    'cScale4': '#777777'\n"
        "    'cScaleLabel4': '#888888'\n"
    )
    fails, passes = mod.check_contrast(diagram)
    assert len(fails) == 1
    assert "WCAG AA" in fails[0]
    assert passes == 0


def test_contrast_textcolor_pairing(scripts_path):
    mod = _import(scripts_path)
    # primaryTextColor pairs with primaryColor per _pair_name convention.
    diagram = (
        "    'primaryColor': '#ffffff'\n"
        "    'primaryTextColor': '#000000'\n"
    )
    fails, passes = mod.check_contrast(diagram)
    assert fails == []
    assert passes == 1


def test_contrast_no_pairs_when_base_absent(scripts_path):
    mod = _import(scripts_path)
    # Label var present but its base is not declared -> nothing checked.
    diagram = "    'cScaleLabel4': '#000000'\n"
    fails, passes = mod.check_contrast(diagram)
    assert fails == []
    assert passes == 0


# ---------------------------------------------------------------------------
# check_state_ids
# ---------------------------------------------------------------------------

def test_state_ids_skipped_when_no_explicit_decls(scripts_path):
    mod = _import(scripts_path)
    diagram = "stateDiagram-v2\n  A --> B\n"
    fails, refs = mod.check_state_ids(diagram)
    assert fails == []
    assert refs == 0


def test_state_ids_pass_all_declared(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "stateDiagram-v2\n"
        '  state "Discover" as Disc\n'
        '  state "Deliver" as Del\n'
        "  [*] --> Disc\n"
        "  Disc --> Del\n"
        "  Del --> [*]\n"
    )
    fails, refs = mod.check_state_ids(diagram)
    assert fails == []
    assert refs > 0


def test_state_ids_fail_undeclared_transition_endpoint(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "stateDiagram-v2\n"
        '  state "Discover" as Disc\n'
        "  Disc --> Ghost\n"
    )
    fails, refs = mod.check_state_ids(diagram)
    assert any("Ghost" in f for f in fails)
    assert refs >= 1


def test_state_ids_fail_undeclared_class_target(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "stateDiagram-v2\n"
        '  state "Discover" as Disc\n'
        "  Disc --> Disc\n"
        "  class Phantom active\n"
    )
    fails, _ = mod.check_state_ids(diagram)
    assert any("Phantom" in f and "class" in f for f in fails)


def test_state_ids_colon_label_decl_counts_as_declared(scripts_path):
    mod = _import(scripts_path)
    diagram = (
        "stateDiagram-v2\n"
        '  state "Discover" as Disc\n'
        "  Other : a label\n"
        "  Disc --> Other\n"
    )
    fails, _ = mod.check_state_ids(diagram)
    assert fails == []


# ---------------------------------------------------------------------------
# check_cli (fail-open)
# ---------------------------------------------------------------------------

def test_check_cli_fail_open_when_mmdc_absent(scripts_path, monkeypatch):
    mod = _import(scripts_path)
    monkeypatch.setattr(mod.shutil, "which", lambda _: None)
    fails, note = mod.check_cli("stateDiagram-v2\n  A --> B")
    assert fails == []
    assert "mmdc not on PATH" in note


# ---------------------------------------------------------------------------
# validate + main
# ---------------------------------------------------------------------------

def test_validate_clean_diagram_no_fails(scripts_path):
    mod = _import(scripts_path)
    text = "```mermaid\nstateDiagram-v2\n  A --> B\n```"
    fails, notes = mod.validate(text)
    assert fails == []
    assert any("skipped" in n for n in notes)


def test_validate_flags_contrast_failure(scripts_path):
    mod = _import(scripts_path)
    text = (
        "```mermaid\n"
        "    'cScale4': '#777777'\n"
        "    'cScaleLabel4': '#888888'\n"
        "```"
    )
    fails, notes = mod.validate(text)
    assert len(fails) == 1
    assert any("FAIL" in n for n in notes)


def test_main_exit_0_on_clean_file(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    f = tmp_path / "diagram.mmd"
    f.write_text("```mermaid\nstateDiagram-v2\n  A --> B\n```")
    rc = mod.main(["validate_mermaid.py", str(f)])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_main_exit_1_on_failing_file(scripts_path, tmp_path, capsys):
    mod = _import(scripts_path)
    f = tmp_path / "bad.mmd"
    f.write_text(
        "```mermaid\n"
        "    'cScale4': '#777777'\n"
        "    'cScaleLabel4': '#888888'\n"
        "```"
    )
    rc = mod.main(["validate_mermaid.py", str(f)])
    assert rc == 1
    assert "not render-safe" in capsys.readouterr().out


def test_main_reads_stdin_on_dash(scripts_path, monkeypatch, capsys):
    mod = _import(scripts_path)
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("stateDiagram-v2\n  A --> B\n"))
    rc = mod.main(["validate_mermaid.py", "-"])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out
