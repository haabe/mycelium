#!/usr/bin/env python3
"""check_system_card_hooks.py — the system card must be re-read when the hooks change.

WHY THIS EXISTS (dogfood, /xai-check 2026-06-11 and again 2026-09-14). `docs/ai-system-card.md`
is the published disclosure of what the AI layer does to the person using it. Twice now it fell
behind the hooks by exactly the mechanism that matters: 2026-06-11 it was silent on autonomous
mode for six patches; 2026-09-14 it was silent on five behaviours shipped in one week — a Stop
hook that refuses to end a turn without a next action, a proposal sent to the human as a
systemMessage on resume, an advisory ledger that mutes a warning after seven ignored sessions,
ruling slots on the diamond, and canvas prose delimited as untrusted. Both times an audit found
it, and the release path had let every one of those releases through, because the only things the
release path syncs on the card are the version and the skill count (`sync_derived.py`).

WHAT IT CHECKS. The card carries one line:

    - **Hook surface reviewed:** YYYY-MM-DD (digest <12 hex>)

The digest is over every file in `plugins/mycelium/hooks/` plus `plugins/mycelium/manifest.yml` —
the set that decides what runs at the human's boundaries and what reaches their screen. When the
digest on disk differs from the digest in the card, this gate fails and prints the files that
changed relative to nothing in particular: it cannot know WHICH hook changed (that needs git
history, which CI's shallow clone does not have), only THAT the surface the card describes moved
since a human last said the card matched it. The remedy is a read, then `--write`.

WHAT IT DOES NOT DO. It cannot tell a typo fix from a new blocking hook; both change the digest,
and both cost the reviewer one read of the diff and one `--write`. That cost is the point: the
alternative, measured twice, is a disclosure document that describes the framework as it was a
quarter ago. It does not check that the card's prose is RIGHT — that stays with `/xai-check` on
cadence. A card with no review line is a precondition failure (exit 2), not a pass.

SECOND READER (v0.310.20, dogfood /xai-check 2026-10-03). `docs/context-surface.md` describes the
same hook layer for practitioners: which hook injects the contract, what reaches the human. It was
not stamped, so when 0.310.16 moved the contract from session-start.sh to contract-part.sh the card
was re-read and context-surface.md went on saying session-start.sh. Every document in `DOCS` now
carries its own review line against the same digest and is checked on its own, so a drift message
names the document to read. A listed document that is missing is a precondition failure, not a
pass.

Exit codes: 0 every digest matches; 1 a digest differs; 2 precondition (a listed document missing,
no review line, no hooks).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

CARD_REL = "docs/ai-system-card.md"
CONTEXT_SURFACE_REL = "docs/context-surface.md"
HOOKS_REL = "plugins/mycelium/hooks"
MANIFEST_REL = "plugins/mycelium/manifest.yml"
REVIEW_RE = re.compile(
    r"^(?:- )?\*\*Hook surface reviewed:\*\* (\d{4}-\d{2}-\d{2}) \(digest ([0-9a-f]{12})\)",
    re.MULTILINE,
)
DIGEST_LEN = 12

# Every document that describes the hook surface to a human. Each entry: path, the line the review
# stamp goes after (regex and its label for errors), the prefix the stamp line carries in that
# document's own style, and what to re-read when the hooks move.
DOCS = (
    {"rel": CARD_REL, "anchor": r"^- \*\*Last updated:\*\*.*$",
     "anchor_label": "- **Last updated:**", "prefix": "- ", "reread": "§2, §3, §5, §6"},
    {"rel": CONTEXT_SURFACE_REL, "anchor": r"^\*\*Last updated\*\*:.*$",
     "anchor_label": "**Last updated**:", "prefix": "",
     "reread": "the session-start paragraph and the Hooks table"},
)


def hook_surface_files(root: Path) -> list[Path]:
    """Every regular file under hooks/ plus the manifest, sorted; empty when hooks/ is absent."""
    hooks = root / HOOKS_REL
    if not hooks.is_dir():
        return []
    files = sorted(p for p in hooks.rglob("*") if p.is_file())
    manifest = root / MANIFEST_REL
    if manifest.is_file():
        files.append(manifest)
    return files


def surface_digest(root: Path) -> str:
    """A short, stable digest of the hook surface: relative path plus bytes, per file."""
    h = hashlib.sha256()
    for p in hook_surface_files(root):
        h.update(str(p.relative_to(root)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:DIGEST_LEN]


def recorded_review(text: str) -> tuple[str, str] | None:
    m = REVIEW_RE.search(text)
    return (m.group(1), m.group(2)) if m else None


def evaluate_doc(root: Path, doc: dict, actual: str) -> dict:
    """One document's review against the current digest."""
    path = root / doc["rel"]
    if not path.is_file():
        return {"rel": doc["rel"], "status": "precondition",
                "detail": f"no {doc['rel']} under {root}"}
    rec = recorded_review(path.read_text(encoding="utf-8"))
    if rec is None:
        return {
            "rel": doc["rel"], "status": "precondition",
            "detail": (f"{doc['rel']} carries no '{doc['prefix']}**Hook surface reviewed:** "
                       f"YYYY-MM-DD (digest ...)' line; add one with --write after reading it "
                       f"against the hooks"),
        }
    date, recorded = rec
    return {"rel": doc["rel"], "status": "ok" if recorded == actual else "drift",
            "reviewed": date, "recorded": recorded, "reread": doc["reread"]}


def evaluate(root: Path) -> dict:
    files = hook_surface_files(root)
    if not files:
        return {"status": "precondition", "detail": f"no hook files under {root / HOOKS_REL}",
                "docs": []}
    actual = surface_digest(root)
    docs = [evaluate_doc(root, d, actual) for d in DOCS]
    pre = [d for d in docs if d["status"] == "precondition"]
    if pre:
        return {"status": "precondition", "detail": "; ".join(d["detail"] for d in pre),
                "docs": docs}
    status = "drift" if any(d["status"] == "drift" for d in docs) else "ok"
    return {"status": status, "actual": actual, "files": len(files), "docs": docs}


def stamp_doc(root: Path, doc: dict, digest: str, stamp: str) -> None:
    path = root / doc["rel"]
    text = path.read_text(encoding="utf-8")
    line = f"{doc['prefix']}**Hook surface reviewed:** {stamp} (digest {digest})"
    if REVIEW_RE.search(text):
        text = REVIEW_RE.sub(line, text, count=1)
    else:
        anchor = re.search(doc["anchor"], text, re.MULTILINE)
        if anchor is None:
            raise ValueError(f"{doc['rel']} has no '{doc['anchor_label']}' line to anchor on")
        text = text[: anchor.end()] + "\n" + line + text[anchor.end():]
    path.write_text(text, encoding="utf-8")


def write_review(root: Path, today: datetime.date | None = None) -> str:
    """Stamp today's date and the current digest into every document; returns the digest.

    All anchors are checked before anything is written, so a failure leaves no document
    half-stamped."""
    digest = surface_digest(root)
    stamp = (today or datetime.datetime.now(datetime.UTC).date()).isoformat()
    for doc in DOCS:
        path = root / doc["rel"]
        if not path.is_file():
            raise ValueError(f"no {doc['rel']} under {root}")
        text = path.read_text(encoding="utf-8")
        if not REVIEW_RE.search(text) and not re.search(doc["anchor"], text, re.MULTILINE):
            raise ValueError(f"{doc['rel']} has no '{doc['anchor_label']}' line to anchor on")
    for doc in DOCS:
        stamp_doc(root, doc, digest, stamp)
    return digest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--write", action="store_true",
                    help=("after reading every document in DOCS against the hooks: "
                          "stamp today and the digest in each"))
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.write:
        try:
            digest = write_review(root)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Hook surface review stamped in {len(DOCS)} documents: digest {digest}.")
        return 0

    result = evaluate(root)
    if result["status"] == "precondition":
        print(f"error: {result['detail']}", file=sys.stderr)
        return 2
    if result["status"] == "drift":
        stale = [d for d in result["docs"] if d["status"] == "drift"]
        print(
            f"Hook surface review: STALE — the hook surface ({result['files']} files under "
            f"{HOOKS_REL} plus the manifest) has digest {result['actual']}. Something that runs "
            f"at the human's boundary changed since these documents were last read against it:"
        )
        for d in stale:
            print(f"  - {d['rel']} (reviewed {d['reviewed']} against {d['recorded']}): "
                  f"re-read {d['reread']}")
        print(
            "Update what the change made untrue, then run this script with --write. A typo fix "
            "costs the same read; that is the price of documents that are never a quarter behind."
        )
        return 1
    reviewed = ", ".join(f"{d['rel']} {d['reviewed']}" for d in result["docs"])
    print(
        f"Hook surface review: OK — digest {result['actual']} over {result['files']} files; "
        f"reviewed: {reviewed}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
