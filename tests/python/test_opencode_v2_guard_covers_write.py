"""The opencode 2.x plugin's read-before-edit guard covers `write`, not only `edit` (v0.328.1).

WHAT WAS WRONG. plugins-v2/mycelium/index.ts guarded `event.tool === "edit"` on the comment
"`write` and `patch` are now `edit`". opencode 2.0.5 and 2.1.1 list a separate `write` tool (and
no `patch`). Run on 2.1.1 with llama3.1:8b on 2026-10-20: `write` to an existing file never read
replaced it. The guard also compared raw path strings, so a relative read and an absolute edit
of the same file did not match.

HOW THIS TEST REACHES A TYPESCRIPT PLUGIN. It copies index.ts into a temporary folder beside a
stub `@opencode/plugin` (whose `Plugin.define` returns its argument), runs it under Node's type
stripping, calls `setup` with a fake context that records the hooks, and drives `execute.before`.
It needs Node 22.6 or later; without it the test SKIPS and says so. CI installs Python only, so on
a runner without such a Node this is a skip there, not a pass: the opencode runtime itself was
exercised by hand on 2.1.1 (roadmap landscape.yml#comp-075, 2026-10-20).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_TS = ROOT / "plugins" / "mycelium" / "integrations" / "opencode" / "plugins-v2" / "mycelium" / "index.ts"

DRIVER = r"""
import { writeFileSync } from "node:fs"
import { join } from "node:path"
const mod = await import(process.argv[2])
const dir = process.argv[3]
const hooks = {}
const ctx = {
  location: { directory: dir },
  session: { hook: async (name, fn) => { hooks["session." + name] = fn } },
  tool: { hook: async (name, fn) => { hooks["tool." + name] = fn } },
}
await mod.default.setup(ctx)
const before = hooks["tool.execute.before"]
const call = (sessionID, tool, input) => {
  try { before({ sessionID, tool, input }); return "allowed" } catch (e) { return "refused" }
}
writeFileSync(join(dir, "existing.txt"), "keep me")
const out = {
  write_existing_unread: call("s1", "write", { path: "existing.txt", content: "x" }),
  write_new_file: call("s1", "write", { path: "brand-new.txt", content: "x" }),
  edit_unread: call("s1", "edit", { path: "existing.txt" }),
}
call("s2", "read", { path: "existing.txt" })
out.edit_after_relative_read_absolute_path = call("s2", "edit", { path: join(dir, "existing.txt") })
out.write_after_read = call("s2", "write", { path: "existing.txt", content: "x" })
console.log(JSON.stringify(out))
"""


def _node() -> str | None:
    node = shutil.which("node")
    if not node:
        return None
    m = re.match(r"v(\d+)\.(\d+)", subprocess.run([node, "--version"], capture_output=True, text=True, check=False).stdout)
    if not m or (int(m.group(1)), int(m.group(2))) < (22, 6):
        return None
    return node


def _run(tmp_path: Path) -> dict:
    node = _node()
    if not node:
        pytest.skip("needs Node 22.6+ to run the opencode plugin's TypeScript; none found")
    pkg = tmp_path / "node_modules" / "@opencode" / "plugin"
    pkg.mkdir(parents=True)
    (pkg / "package.json").write_text(json.dumps({"name": "@opencode/plugin", "type": "module", "main": "index.js"}))
    (pkg / "index.js").write_text("export const Plugin = { define: (d) => d }\n")
    (tmp_path / "package.json").write_text(json.dumps({"type": "module"}))
    shutil.copy(PLUGIN_TS, tmp_path / "index.ts")
    (tmp_path / "driver.mjs").write_text(DRIVER)
    work = tmp_path / "work"
    work.mkdir()
    r = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(tmp_path / "driver.mjs"),
         str(tmp_path / "index.ts"), str(work)],
        capture_output=True, text=True, cwd=work, timeout=60, check=False,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_write_to_an_existing_unread_file_is_refused(tmp_path):
    assert _run(tmp_path)["write_existing_unread"] == "refused"


def test_write_that_creates_a_new_file_is_allowed(tmp_path):
    assert _run(tmp_path)["write_new_file"] == "allowed"


def test_edit_without_a_read_is_still_refused(tmp_path):
    assert _run(tmp_path)["edit_unread"] == "refused"


def test_a_relative_read_covers_an_absolute_edit_of_the_same_file(tmp_path):
    out = _run(tmp_path)
    assert out["edit_after_relative_read_absolute_path"] == "allowed"
    assert out["write_after_read"] == "allowed"


def test_the_comment_no_longer_says_write_is_edit():
    text = PLUGIN_TS.read_text(encoding="utf-8")
    assert "`write` and `patch` are now `edit`" not in text
