"""Coverage proof for check_system_card_hooks.py, and proof that it bites.

The gate exists because the AI system card fell behind the hooks twice (2026-06-11, 2026-09-14)
and the release path had no reader of the card beyond its version token. Every test that
matters plants a hook change and requires it to be FOUND; the precondition tests pin the
anti-pattern-#9 shape (a missing review line is not a pass).
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "plugins" / "mycelium" / "scripts" / "check_system_card_hooks.py"
sys.path.insert(0, str(SCRIPT.parent))
import check_system_card_hooks as csch  # noqa: E402

CARD = "# AI System Card\n\n## 1. Identity\n\n- **Version:** 0.1.0\n- **Last updated:** 2026-01-01\n- **Maintained by:** x\n"


def _tree(tmp_path, hooks=("a.sh",), manifest=True):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "ai-system-card.md").write_text(CARD)
    hd = root / "plugins" / "mycelium" / "hooks"
    hd.mkdir(parents=True)
    for h in hooks:
        (hd / h).write_text(f"#!/bin/bash\necho {h}\n")
    if manifest:
        (root / "plugins" / "mycelium" / "manifest.yml").write_text("hooks: {}\n")
    return root


def test_write_then_check_is_ok(tmp_path, capsys):
    root = _tree(tmp_path)
    assert csch.main(["--root", str(root), "--write"]) == 0
    assert csch.main(["--root", str(root)]) == 0
    assert "OK" in capsys.readouterr().out


def test_a_changed_hook_is_found(tmp_path, capsys):
    root = _tree(tmp_path)
    csch.main(["--root", str(root), "--write"])
    (root / "plugins/mycelium/hooks/a.sh").write_text("#!/bin/bash\nexit 2  # now blocking\n")
    assert csch.main(["--root", str(root)]) == 1
    assert "STALE" in capsys.readouterr().out


def test_a_new_hook_file_is_found(tmp_path):
    root = _tree(tmp_path)
    csch.main(["--root", str(root), "--write"])
    (root / "plugins/mycelium/hooks/b.sh").write_text("#!/bin/bash\n")
    assert csch.main(["--root", str(root)]) == 1


def test_a_manifest_change_is_found(tmp_path):
    root = _tree(tmp_path)
    csch.main(["--root", str(root), "--write"])
    (root / "plugins/mycelium/manifest.yml").write_text("hooks: {timeout: 5}\n")
    assert csch.main(["--root", str(root)]) == 1


def test_a_missing_review_line_is_a_precondition_not_a_pass(tmp_path, capsys):
    root = _tree(tmp_path)
    assert csch.main(["--root", str(root)]) == 2
    assert "no '- **Hook surface reviewed:**" in capsys.readouterr().err


def test_no_card_and_no_hooks_are_preconditions(tmp_path, capsys):
    root = _tree(tmp_path)
    (root / "docs/ai-system-card.md").unlink()
    assert csch.main(["--root", str(root)]) == 2
    root2 = _tree(tmp_path / "two", hooks=())
    assert csch.main(["--root", str(root2)]) == 2


def test_write_replaces_an_existing_line_and_stamps_the_date(tmp_path):
    root = _tree(tmp_path)
    csch.write_review(root, today=datetime.date(2026, 9, 14))
    csch.write_review(root, today=datetime.date(2026, 9, 15))
    text = (root / "docs/ai-system-card.md").read_text()
    assert text.count("Hook surface reviewed") == 1
    assert "2026-09-15 (digest " in text
    assert text.index("**Last updated:**") < text.index("Hook surface reviewed")


def test_write_without_an_anchor_fails_loud(tmp_path, capsys):
    root = _tree(tmp_path)
    (root / "docs/ai-system-card.md").write_text("# card with no identity block\n")
    assert csch.main(["--root", str(root), "--write"]) == 2
    assert "no '- **Last updated:**'" in capsys.readouterr().err


def test_digest_is_stable_across_runs_and_sensitive_to_path(tmp_path):
    root = _tree(tmp_path, hooks=("a.sh", "b.sh"))
    d1 = csch.surface_digest(root)
    assert d1 == csch.surface_digest(root)
    (root / "plugins/mycelium/hooks/b.sh").rename(root / "plugins/mycelium/hooks/c.sh")
    assert csch.surface_digest(root) != d1
