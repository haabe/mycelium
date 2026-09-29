#!/usr/bin/env python3
"""Derive hooks/hooks.codex-plugin.json from hooks/hooks.codex.json (v0.286.0).

WHY TWO FILES. hooks.codex.json is a template for install-runtime-hooks.sh, which bakes the
plugin's real path into a project's .codex/hooks.json. A plugin installed from a marketplace
never runs that installer: Codex reads the plugin's own manifest, and with no `hooks` key it
falls back to hooks/hooks.json, the Claude Code file. On Codex that file loses its four `async`
hooks at load (change-log, read-log, diamond-state-audit, the heavy session-start tier) and has
an event Codex does not know (PostToolUseFailure). Measured 2026-09-29 on Codex CLI 0.158.0.

Codex sets CLAUDE_PLUGIN_ROOT for plugin hooks ("for compatibility with existing plugin hooks"),
and a run on hooks.json proved it resolves, so the derived file uses it in place of the
placeholder. Everything else is copied, so the two files cannot drift apart: the test runs this
with --check.

Usage: codex_plugin_hooks.py [--root DIR] [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLACEHOLDER = "__MYCELIUM_PLUGIN_ROOT__"
ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"
SOURCE = Path("hooks") / "hooks.codex.json"
TARGET = Path("hooks") / "hooks.codex-plugin.json"
DESCRIPTION = (
    "GENERATED from hooks.codex.json by scripts/codex_plugin_hooks.py; do not edit by hand. "
    "The hooks Codex CLI runs for a marketplace install, named by .codex-plugin/plugin.json. "
    "Same hooks as hooks.codex.json with the plugin root taken from CLAUDE_PLUGIN_ROOT, which "
    "Codex sets for plugin hooks. Codex runs none of them until the user trusts them in /hooks."
)


def derive(plugin_root: Path) -> str:
    src = json.loads((plugin_root / SOURCE).read_text(encoding="utf-8"))
    # Codex accepts exactly `description` and `hooks` at the top level: "unknown field
    # `_description`, expected `description` or `hooks`" (Codex CLI 0.158.0, 2026-09-29), and a file
    # it cannot parse loads no hooks at all.
    out = {"description": DESCRIPTION, "hooks": src["hooks"]}
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    return text.replace(PLACEHOLDER, ROOT_VAR)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                    help="the plugin root (default: this script's plugin)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the file is out of date")
    args = ap.parse_args(argv)
    want = derive(args.root)
    target = args.root / TARGET
    have = target.read_text(encoding="utf-8") if target.exists() else ""
    if args.check:
        if have != want:
            print(f"{TARGET} is out of date with {SOURCE}; run scripts/codex_plugin_hooks.py",
                  file=sys.stderr)
            return 1
        return 0
    if have != want:
        target.write_text(want, encoding="utf-8")
        print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
