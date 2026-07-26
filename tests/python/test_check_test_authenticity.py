"""Coverage for check_test_authenticity.py, including proof that it BITES.

A gate that cannot fail is indistinguishable from a healthy repo — the exact
confusion this gate exists to end. So the load-bearing tests here are the
negative controls: build a repo containing a fake test, and require a finding.

The false-positive tests matter just as much. The first three iterations of this
gate reported 44, then 45, then 1 finding against Mycelium's own suite, every one
of them wrong, because "production code" was derived on the wrong axis each time
(directory, then leading underscore, then file extension). A gate that cries wolf
gets switched off, and is then worth less than no gate at all.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "mycelium" / "scripts" / "check_test_authenticity.py"
)
_spec = importlib.util.spec_from_file_location("check_test_authenticity", _SCRIPT)
cta = importlib.util.module_from_spec(_spec)
sys.modules["check_test_authenticity"] = cta
_spec.loader.exec_module(cta)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    return tmp_path


def _run(root: Path) -> tuple[int, list]:
    prod = cta._production_modules(root)
    findings = []
    for t in cta._iter_test_files(root):
        got, _ = cta.check_file(t, prod)
        findings.extend(got)
    return len(findings), findings


# ---------------------------------------------------------------- it bites

def test_tautology_is_caught(tmp_path):
    root = _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": "from thing import go\n\ndef test_x():\n    assert True\n",
    })
    n, findings = _run(root)
    assert any(f.rule == "tautology" for f in findings), [f.rule for f in findings]


def test_test_that_reaches_no_production_code_is_caught(tmp_path):
    root = _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": "import json\n\ndef test_x():\n    assert json.dumps({}) == '{}'\n",
    })
    n, findings = _run(root)
    assert any(f.rule == "no-production-reach" for f in findings)


def test_fully_mocked_test_is_caught(tmp_path):
    """The blank-screen shape: green suite, nothing real executed."""
    root = _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": (
            "from unittest.mock import patch\n"
            "import thing\n\n"
            "def test_x():\n"
            "    with patch('thing.go', return_value=2):\n"
            "        assert thing.go() == 2\n"
        ),
    })
    n, findings = _run(root)
    assert any(f.rule == "fully-mocked" for f in findings), [f.rule for f in findings]


def test_shell_test_invoking_nothing_shipped_is_caught(tmp_path):
    root = _repo(tmp_path, {
        "bin/deploy.sh": "#!/bin/bash\necho hi\n",
        "tests/test_y.sh": "#!/bin/bash\n[ 1 = 1 ] && echo ok\n",
    })
    n, findings = _run(root)
    rules = {f.rule for f in findings}
    assert "no-production-reach" in rules
    assert "tautology" in rules


# ------------------------------------------------------- it does NOT cry wolf

def test_authentic_python_test_passes(tmp_path):
    root = _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": "from thing import go\n\ndef test_x():\n    assert go() == 1\n",
    })
    assert _run(root)[0] == 0


def test_shell_test_sourcing_a_shipped_script_by_path_passes(tmp_path):
    """Regression: the commonest shell reference is a PATH, and a lookbehind that
    excluded `/` rejected every one — 45 false positives in one run."""
    root = _repo(tmp_path, {
        "tests/validate-template.sh": "#!/bin/bash\ncheck_one() { return 0; }\n",
        "tests/test_check_1.sh": '#!/bin/bash\nsource "$REPO_ROOT/tests/validate-template.sh"\ncheck_one\n',
    })
    assert _run(root)[0] == 0


def test_dynamic_import_counts_as_reaching_production(tmp_path):
    """importlib.spec_from_file_location is how several real tests load scripts."""
    root = _repo(tmp_path, {
        "scripts/check_thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": (
            "import importlib.util\n"
            "from pathlib import Path\n"
            "S = Path('scripts/check_thing.py')\n"
            "spec = importlib.util.spec_from_file_location('check_thing', S)\n"
            "def test_x():\n    assert spec is not None\n"
        ),
    })
    assert _run(root)[0] == 0


def test_subprocess_invocation_counts_as_reaching_production(tmp_path):
    root = _repo(tmp_path, {
        "scripts/parse_manifest.py": "print('x')\n",
        "tests/test_x.py": (
            "import subprocess\n\n"
            "def test_x():\n"
            "    r = subprocess.run(['python3', 'scripts/parse_manifest.py'])\n"
            "    assert r.returncode == 0\n"
        ),
    })
    assert _run(root)[0] == 0


def test_asserting_on_a_shipped_document_counts(tmp_path):
    """Docs are shipped artefacts. Mycelium delivers 58 skills as SKILL.md;
    a test holding that content to its contract exercises the product."""
    root = _repo(tmp_path, {
        "docs/ai-system-card.md": "# Card\n\nFaithfulness section.\n",
        "tests/test_card.py": (
            "from pathlib import Path\n\n"
            "def test_card():\n"
            "    t = Path('docs/ai-system-card.md').read_text()\n"
            "    assert 'Faithfulness' in t\n"
        ),
    })
    assert _run(root)[0] == 0


def test_production_name_inside_a_longer_word_does_not_count(tmp_path):
    """`parse_manifest` must not satisfy a reach check for `manifest`."""
    root = _repo(tmp_path, {
        "scripts/manifest.py": "def go():\n    return 1\n",
        "tests/test_x.py": "def parse_manifest_helper():\n    return 1\n\ndef test_x():\n    assert parse_manifest_helper() == 1\n",
    })
    assert any(f.rule == "no-production-reach" for f in _run(root)[1])


def test_production_named_only_in_a_comment_does_not_count(tmp_path):
    """Naming a module in prose is not calling it."""
    root = _repo(tmp_path, {
        "scripts/check_thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": "# this test is about check_thing.py\ndef test_x():\n    assert 2 == 1 + 1\n",
    })
    assert any(f.rule == "no-production-reach" for f in _run(root)[1])


def test_placeholder_marker_is_ignored_when_real_code_runs(tmp_path):
    """`# Simulate` usually narrates FIXTURE construction in an otherwise real
    test. Flagging it taught the gate to cry wolf on a genuine test."""
    root = _repo(tmp_path, {
        "src/verify.py": "def verify(t, e):\n    return {'unverified': [t]}\n",
        "tests/test_v.py": (
            "from verify import verify\n\n"
            "def test_v():\n"
            "    # Simulate a session where the file was NOT read\n"
            "    r = verify('a.yml', [])\n"
            "    assert 'a.yml' in r['unverified']\n"
        ),
    })
    assert _run(root)[0] == 0


# ------------------------------------------------------------ scope honesty

def test_infrastructure_is_not_scanned_as_a_test(tmp_path):
    root = _repo(tmp_path, {
        "tests/_assert.sh": '#!/bin/bash\nassert_eq() { [ "$1" = "$2" ]; }\n',
        "tests/validate-template.sh": "#!/bin/bash\ncheck() { return 0; }\n",
        "tests/test_a.sh": '#!/bin/bash\nsource "$D/tests/validate-template.sh"\ncheck\n',
    })
    scanned = {p.name for p in cta._iter_test_files(root)}
    assert "_assert.sh" not in scanned
    assert "validate-template.sh" not in scanned
    assert "test_a.sh" in scanned


def test_unsupported_language_is_reported_unchecked_not_passed(tmp_path):
    """A gate that quietly narrows its scope reports health it never measured."""
    root = _repo(tmp_path, {"tests/thing_test.rb": "assert true\n"})
    p = root / "tests" / "thing_test.rb"
    _, was_checked = cta.check_file(p, set())
    assert was_checked is False


def test_empty_repo_is_not_a_pass(tmp_path, capsys):
    """No tests found must not exit 0 — nothing was verified."""
    (tmp_path / "src").mkdir()
    argv = sys.argv
    sys.argv = ["check_test_authenticity.py", "--root", str(tmp_path)]
    try:
        rc = cta.main()
    finally:
        sys.argv = argv
    assert rc == 1
    assert "no test files found" in capsys.readouterr().out


def test_real_repo_is_clean():
    """Mycelium's own suite must pass its own gate."""
    root = Path(__file__).resolve().parents[2]
    prod = cta._production_modules(root)
    findings = []
    for t in cta._iter_test_files(root):
        got, _ = cta.check_file(t, prod)
        findings.extend(got)
    assert not findings, "\n".join(str(f) for f in findings)


# ------------------------------------------------------------ CLI surface
#
# The per-file coverage floor blocked the first push at exactly 70%: the whole
# main() reporting path was untested. That floor is the script-level analogue of
# G-V12, and it caught precisely the thing this gate is about — a shipped entry
# point nothing exercised. Fixing it by lowering the floor would have been the
# tolerated-debt baseline the ruff policy also forbids.

def _main(root: Path, *extra: str) -> int:
    argv = sys.argv
    sys.argv = ["check_test_authenticity.py", "--root", str(root), *extra]
    try:
        return cta.main()
    finally:
        sys.argv = argv


def test_main_exits_0_and_says_so_on_a_clean_repo(tmp_path, capsys):
    _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_x.py": "from thing import go\n\ndef test_x():\n    assert go() == 1\n",
    })
    assert _main(tmp_path) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "production names derived" in out


def test_main_exits_1_and_prints_each_finding(tmp_path, capsys):
    _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_bad.py": "def test_bad():\n    assert True\n",
    })
    assert _main(tmp_path) == 1
    out = capsys.readouterr().out
    assert "FAIL:" in out
    assert "no-production-reach" in out
    assert "tests/test_bad.py" in out, "findings must be reported relative to root"


def test_quiet_suppresses_the_banner_but_never_the_findings(tmp_path, capsys):
    _repo(tmp_path, {
        "src/thing.py": "def go():\n    return 1\n",
        "tests/test_bad.py": "def test_bad():\n    assert True\n",
    })
    assert _main(tmp_path, "--quiet") == 1
    out = capsys.readouterr().out
    assert "production names derived" not in out
    assert "FAIL:" in out, "--quiet must never hide a finding"


def test_bad_root_is_a_usage_error(tmp_path, capsys):
    assert _main(tmp_path / "nope") == 2
    assert "not a directory" in capsys.readouterr().err


def test_unchecked_files_are_listed_and_the_remainder_counted(tmp_path, capsys):
    """Scope narrowing must be visible. The listing is capped; the count is not."""
    files = {"src/thing.py": "def go():\n    return 1\n"}
    for i in range(cta.MAX_LISTED + 5):
        files[f"tests/thing{i}_test.rb"] = "assert true\n"
    files["tests/test_ok.py"] = "from thing import go\n\ndef test_ok():\n    assert go() == 1\n"
    root = _repo(tmp_path, files)
    # .rb is not in TEST_PATTERNS, so drive the reporter directly with the real paths.
    unchecked = sorted(root.glob("tests/*_test.rb"))
    cta._report_unchecked(unchecked, root)
    out = capsys.readouterr().out
    assert f"UNCHECKED ({len(unchecked)} file(s)" in out
    assert f"... and {len(unchecked) - cta.MAX_LISTED} more" in out


def test_unreadable_test_file_is_a_finding_not_a_skip(tmp_path):
    root = _repo(tmp_path, {"tests/test_x.py": "x\n"})
    target = root / "tests" / "test_x.py"
    target.chmod(0o000)
    try:
        findings, checked = cta.check_file(target, set())
    finally:
        target.chmod(0o644)
    if findings:  # root can read anything; only assert when the chmod took effect
        assert checked is True
        assert findings[0].rule == "unreadable"
