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

Exit codes: 0 digest matches; 1 digest differs; 2 precondition (no card, no review line, no hooks).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import sys
from pathlib import Path

CARD_REL = "docs/ai-system-card.md"
HOOKS_REL = "plugins/mycelium/hooks"
MANIFEST_REL = "plugins/mycelium/manifest.yml"
REVIEW_RE = re.compile(
    r"^- \*\*Hook surface reviewed:\*\* (\d{4}-\d{2}-\d{2}) \(digest ([0-9a-f]{12})\)", re.MULTILINE
)
DIGEST_LEN = 12


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


def recorded_review(card_text: str) -> tuple[str, str] | None:
    m = REVIEW_RE.search(card_text)
    return (m.group(1), m.group(2)) if m else None


def evaluate(root: Path) -> dict:
    card = root / CARD_REL
    if not card.is_file():
        return {"status": "precondition", "detail": f"no {CARD_REL} under {root}"}
    files = hook_surface_files(root)
    if not files:
        return {"status": "precondition", "detail": f"no hook files under {root / HOOKS_REL}"}
    text = card.read_text(encoding="utf-8")
    rec = recorded_review(text)
    if rec is None:
        return {
            "status": "precondition",
            "detail": (f"{CARD_REL} carries no '- **Hook surface reviewed:** YYYY-MM-DD "
                       f"(digest ...)' line; add one with --write after reading the card "
                       f"against the hooks"),
        }
    date, recorded = rec
    actual = surface_digest(root)
    status = "ok" if recorded == actual else "drift"
    return {"status": status, "reviewed": date, "recorded": recorded, "actual": actual,
            "files": len(files)}


def write_review(root: Path, today: datetime.date | None = None) -> str:
    """Stamp today's date and the current digest into the card; returns the new digest."""
    card = root / CARD_REL
    text = card.read_text(encoding="utf-8")
    digest = surface_digest(root)
    stamp = (today or datetime.datetime.now(datetime.UTC).date()).isoformat()
    line = f"- **Hook surface reviewed:** {stamp} (digest {digest})"
    if REVIEW_RE.search(text):
        text = REVIEW_RE.sub(line, text, count=1)
    else:
        anchor = re.search(r"^- \*\*Last updated:\*\*.*$", text, re.MULTILINE)
        if anchor is None:
            raise ValueError(f"{CARD_REL} has no '- **Last updated:**' line to anchor on")
        text = text[: anchor.end()] + "\n" + line + text[anchor.end():]
    card.write_text(text, encoding="utf-8")
    return digest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--write", action="store_true",
                    help="after reading the card against the hooks: stamp today and the digest")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.write:
        try:
            digest = write_review(root)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"System card hook review stamped: digest {digest}.")
        return 0

    result = evaluate(root)
    if result["status"] == "precondition":
        print(f"error: {result['detail']}", file=sys.stderr)
        return 2
    if result["status"] == "drift":
        print(
            f"System card hook review: STALE — the hook surface ({result['files']} files under "
            f"{HOOKS_REL} plus the manifest) has digest {result['actual']}; the card was last "
            f"reviewed against {result['recorded']} on {result['reviewed']}. Something that runs "
            f"at the human's boundary changed. Read the diff against docs/ai-system-card.md "
            f"§2, §3, §5, §6, update what the change made untrue, then run this script with "
            f"--write. A typo fix costs the same read; that is the price of a card that is "
            f"never a quarter behind."
        )
        return 1
    print(
        f"System card hook review: OK — digest {result['actual']} over {result['files']} files, "
        f"reviewed {result['reviewed']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
