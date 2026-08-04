#!/usr/bin/env python3
"""Release-gap detection: which versions landed, and which of them never shipped.

WHY THIS EXISTS. `auto-release.yml` used to read `plugin.json` once, at the tip of
the push, and create exactly one Release for that one version. When a push carried
more than one version bump, every intermediate version was skipped -- and the job
exited 0. On 2026-07-30 seven versions (v0.66.0 through v0.66.6) went by in a single
push. CI was green, nothing was reported, and the gap was found five weeks later by
someone auditing the version chain for an unrelated reason. The changelog documented
all seven; the releases page skipped 0.65.0 -> 0.67.0.

The failure mode is not "the release step broke". It is that **absence produced a
success**: no error, no output, nothing distinguishing "one version, released" from
"seven versions, one released". That is `fail-open-on-absent-input`, and the fix has
to make the skipped case *loud*, not merely less likely.

So this module answers two questions, deliberately kept separate and pure so both can
be tested without a network, a repo, or a GitHub token:

  1. versions_introduced(...)  -- which versions does this push actually add?
  2. missing_releases(...)     -- after releasing, does any known version still lack one?

(2) is the load-bearing half. (1) can be made correct and still drift if a version
arrives some other way -- a manual tag, a revert, a force-push. (2) does not care how
the gap appeared; it re-derives the truth from the changelog every run.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

# Releases begin at 0.49.0. Everything before that predates release automation
# entirely and is history, not drift -- 149 versions were bumped on main in that era
# with no tags at all, and backfilling them would be inventing a record rather than
# repairing one. The floor keeps the gap check honest about what it is claiming.
DEFAULT_FLOOR = "0.49.0"

PLUGIN_JSON = "plugins/mycelium/.claude-plugin/plugin.json"
LEGACY_PLUGIN_JSON = ".claude-plugin/plugin.json"

_VERSION_RE = re.compile(r'"version"\s*:\s*"([^"]+)"')
_CHANGELOG_HEADING_RE = re.compile(r"^## v(\d+\.\d+\.\d+)", re.MULTILINE)


def version_key(v: str) -> tuple:
    """Sort key. Non-numeric or malformed versions sort last rather than crashing."""
    try:
        return (0, *(int(p) for p in v.split(".")))
    except ValueError:
        return (1, v)


def parse_changelog_versions(text: str) -> list[str]:
    """Every version with a `## vX.Y.Z` section. The changelog is the claim of record:
    if a version is documented there, a consumer can reasonably expect a Release."""
    return sorted(set(_CHANGELOG_HEADING_RE.findall(text)), key=version_key)


def version_from_plugin_json(text: str) -> str | None:
    m = _VERSION_RE.search(text or "")
    return m.group(1) if m else None


def missing_releases(
    changelog_versions, released_versions, floor: str = DEFAULT_FLOOR
) -> list[str]:
    """Documented at or above `floor` but never released. Order is ascending.

    Pure on purpose: the caller supplies both lists, so this is testable without gh.
    """
    have = set(released_versions)
    fk = version_key(floor)
    return sorted(
        (v for v in changelog_versions if v not in have and version_key(v) >= fk),
        key=version_key,
    )


def _git(*args: str) -> str:
    r = subprocess.run(("git", *args), capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def _version_at(commit: str) -> str | None:
    for path in (PLUGIN_JSON, LEGACY_PLUGIN_JSON):
        v = version_from_plugin_json(_git("show", f"{commit}:{path}"))
        if v:
            return v
    return None


def versions_introduced(before: str, head: str) -> list[dict]:
    """Versions this push adds, each paired with the commit that first set it.

    Walks the range oldest-first so a version is anchored to where it *appeared*,
    not to the tip -- a backfilled tag pointing at the wrong commit is its own quiet
    lie. A version already present at `before` is not introduced by this push.

    `before` may be absent or all-zeros (first push, force-push, workflow_dispatch);
    in that case only `head` is considered, which degrades to the old one-version
    behaviour rather than failing. The gap check is what catches anything this misses.
    """
    zeroish = (not before) or set(before) <= {"0"}
    if zeroish:
        commits = [head]
        baseline = None
    else:
        rng = _git("rev-list", "--reverse", f"{before}..{head}")
        commits = [c for c in rng.split("\n") if c]
        baseline = _version_at(before)

    seen: dict[str, str] = {}
    if baseline:
        seen[baseline] = before
    out: list[dict] = []
    for c in commits:
        v = _version_at(c)
        if v and v not in seen:
            seen[v] = c
            out.append({"version": v, "commit": c})
    return out


def _released_from_gh() -> list[str]:
    r = subprocess.run(
        ["gh", "release", "list", "--limit", "500", "--json", "tagName"],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        # Fail LOUD. An unreadable release list must never be read as "no gaps" --
        # that is the exact fail-open this script exists to close.
        print(f"::error::could not list releases: {r.stderr.strip()[:300]}", file=sys.stderr)
        raise SystemExit(2)
    return [x["tagName"].lstrip("v") for x in json.loads(r.stdout or "[]")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--introduced", nargs=2, metavar=("BEFORE", "HEAD"),
                    help="print JSON [{version, commit}] introduced by BEFORE..HEAD")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any changelog version at/above the floor has no Release")
    ap.add_argument("--changelog", default="docs/changelog.md")
    ap.add_argument("--floor", default=DEFAULT_FLOOR)
    args = ap.parse_args()

    if args.introduced:
        print(json.dumps(versions_introduced(*args.introduced)))
        return 0

    if args.check:
        with open(args.changelog) as fh:
            documented = parse_changelog_versions(fh.read())
        gaps = missing_releases(documented, _released_from_gh(), args.floor)
        if gaps:
            print(f"::error::{len(gaps)} documented version(s) have no GitHub Release: "
                  + ", ".join("v" + g for g in gaps))
            print("The changelog promises these to consumers and the releases page does not "
                  "have them. Create them, or remove the changelog sections.", file=sys.stderr)
            return 1
        print(f"OK: every changelog version >= v{args.floor} has a Release "
              f"({len(documented)} documented).")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
