"""Guard: every shipped-framework manifest entry must resolve to a source.

Why this exists: manifest.yml is the contract upgrade.sh uses to sync framework
files into an installed project. From the legacy→plugin migration (commit a5cabd3)
until v0.33.0 it listed three framework targets that existed in neither source
tree — `.claude/optimization/`, `.claude/tests/`, and `.claude/tests/README.md`.
upgrade.sh's `[ -d ]`/`[ -e ]` guards made the drift silent (missing sources
no-op), so nothing failed and the dead entries persisted for weeks. A 2026-05-30
reference-graph recon surfaced them. This test fails if any shipped-framework
entry stops resolving again.

Path mapping: manifest paths are runtime-install paths (`.claude/X`). The
canonical source is `plugins/mycelium/X`, but some framework data (canvas
templates, evals scenarios/READMEs) is still tracked at the repo-root `.claude/X`
dogfood tree. An entry resolves if EITHER tree contains it.

Excluded: `project_state` and `evals.preserve` targets are created per-project at
runtime — legitimately absent from the source tree, so they are not checked.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "plugins" / "mycelium" / "scripts"))

from _manifest_lib import parse_manifest  # noqa: E402

MANIFEST = REPO / "plugins" / "mycelium" / "manifest.yml"

# Buckets whose entries ship to installers and MUST have a source on disk.
# project_state is intentionally excluded (runtime-created).
SHIPPED_BUCKETS = [
    "top_level",
    "directories",
    "single_files",
    "harness_framework",
    "preserved_dir_readmes",
    "evals_replace",
    "metrics_adapters_framework",
]


def _resolves(entry: str) -> bool:
    e = entry.rstrip("/")
    if "*" in e:  # glob template (e.g. canvas/*.yml) — not a single concrete path
        return bool(list(REPO.glob(e)))
    cands = [e]
    if e.startswith(".claude/"):
        cands.append("plugins/mycelium/" + e[len(".claude/") :])
    return any((REPO / c).exists() for c in cands)


def test_every_shipped_manifest_entry_has_a_source():
    parsed = parse_manifest(str(MANIFEST))
    dead = []
    for bucket in SHIPPED_BUCKETS:
        for entry in parsed[bucket]:
            if not _resolves(entry):
                dead.append(f"[{bucket}] {entry}")
    assert not dead, (
        "manifest.yml lists shipped-framework targets with no source in either "
        "the plugins/mycelium/ or repo-root .claude/ tree — upgrade.sh would "
        "silently skip them:\n  " + "\n  ".join(dead)
    )
