#!/usr/bin/env python3
"""Compare framework versions RECORDED in canvas files against the one INSTALLED.

WHAT THIS GUARDS. On 2026-08-05 a dogfood canvas was found asserting
`ai-tool-metrics.yml :: model_metrics.version: "Mycelium 0.16.1"` while the
running plugin was 0.89.0 — **73 releases behind**. Nothing anywhere compared a
version a canvas CLAIMS against the version that is actually loaded, so the field
sat wrong for three months and no check could see it. `/canvas-health` reads
`_meta.version` (an integer schema revision) and never looks at prose version
strings; `sync_derived.py` syncs docs, not canvases.

Why a canvas records a framework version at all: system-card and AI-tool metric
fields describe the product being assessed, and for this framework the product IS
the plugin. A regulatory or model-metrics field naming a stale version misstates
what was assessed.

SCOPE, deliberately narrow. It inspects values under keys literally named
`version` (excluding `schema_version` and integer `_meta.version`) that contain a
semver AND sit next to a framework marker word. It does NOT scan free prose:
canvases legitimately cite historical versions ("shipped in v0.70.0", "regression
since 0.61.0"), and flagging those would make the check noise on day one — the
failure mode this project has logged repeatedly.

Exit codes:
    0  no drift (or nothing to check)
    1  at least one canvas claims a version that is not the installed one
    2  the check itself could not run

Python stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("SKIP:pyyaml unavailable", file=sys.stderr)
    sys.exit(3)

SEMVER = re.compile(r"\b(\d+\.\d+\.\d+)\b")
FRAMEWORK_MARKER = re.compile(r"myceli", re.IGNORECASE)


def installed_version(root: Path) -> str | None:
    for rel in ("plugins/mycelium/.claude-plugin/plugin.json", ".claude-plugin/plugin.json"):
        p = root / rel
        if p.exists():
            try:
                return json.loads(p.read_text()).get("version")
            except (json.JSONDecodeError, OSError):
                return None
    return None


def _walk(node, path, out):
    """Collect (path, value) for keys literally named `version` holding a string."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "version" and isinstance(v, str):
                out.append((f"{path}.{k}", v))
            elif k != "schema_version":
                _walk(v, f"{path}.{k}", out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk(v, f"{path}[{i}]", out)


def scan(root: Path, installed: str) -> list[dict]:
    findings = []
    for f in sorted((root / ".claude" / "canvas").glob("*.yml")):
        try:
            doc = yaml.safe_load(f.read_text()) or {}
        except Exception as exc:  # noqa: BLE001 — an unparseable canvas is another check's job
            # Not silent: say which file was skipped and why. A version check that
            # quietly skips files would report OK over a corpus it never read.
            print(f"  (skipped {f.name}: unparseable — {type(exc).__name__})", file=sys.stderr)
            continue
        hits: list[tuple[str, str]] = []
        _walk(doc, "", hits)
        for path, value in hits:
            # Only a value that BOTH names the framework and carries a semver is a
            # claim about the installed version. Everything else is someone else's
            # version string and none of this check's business.
            if not FRAMEWORK_MARKER.search(value):
                continue
            m = SEMVER.search(value)
            if not m:
                continue
            claimed = m.group(1)
            if claimed != installed:
                findings.append({
                    "file": f.name, "path": path.lstrip("."),
                    "claimed": claimed, "installed": installed,
                    "value": value[:120],
                })
    return findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--framework-root", default=None,
                    help="where plugin.json lives, if not under --root")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    fw = Path(args.framework_root).resolve() if args.framework_root else root
    installed = installed_version(fw)
    if not installed:
        print("Canvas version drift: UNKNOWN — could not read an installed plugin.json "
              f"under {fw}. Not reporting a clean bill of health it did not earn.")
        return 2

    findings = scan(root, installed)
    if not findings:
        print(f"Canvas version drift: OK — no canvas claims a framework version "
              f"other than the installed {installed}.")
        return 0

    print(f"Canvas version drift: {len(findings)} canvas field(s) claim a framework "
          f"version that is not the installed {installed}.\n")
    for f in findings:
        print(f"  {f['file']} :: {f['path']}")
        print(f"      claims {f['claimed']}, installed {f['installed']}")
        print(f"      value: {f['value']}\n")
    print("A canvas field naming a stale framework version misstates what was assessed.\n"
          "Update the field, or if it is deliberately historical, move the version out of a\n"
          "`version:` key and into prose where this check does not read it.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
