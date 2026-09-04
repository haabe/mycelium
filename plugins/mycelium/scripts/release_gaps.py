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


def undocumented_releases(
    released_versions, changelog_versions, floor: str = DEFAULT_FLOOR
) -> list[str]:
    """The INVERSE of `missing_releases`: released at or above `floor` but never
    documented. Ascending.

    WHY THIS DIRECTION EXISTS (2026-09-04). `missing_releases` answers "the changelog
    promised it and the releases page lacks it". Nothing answered the mirror question,
    and the mirror question has a worse failure: a Release nobody meant to cut is a
    public claim about what shipped, where a missing Release is only an absence.

    Two instances, found by measuring rather than by any check. v0.176.0 (2026-09-03)
    was cut because an intermediate commit in a pushed range carried that version in
    plugin.json; it was deleted by hand within the hour. v0.107.1 (2026-08-08) was cut
    the same way, its body reading "see docs/changelog.md" against a changelog with no
    such section -- and it went unnoticed for 27 days, which is what an unmeasured
    direction looks like.

    Pure on purpose, same as its mirror: the caller supplies both lists.
    """
    documented = set(changelog_versions)
    fk = version_key(floor)
    return sorted(
        (v for v in released_versions if v not in documented and version_key(v) >= fk),
        key=version_key,
    )


def partition_undocumented(introduced, documented) -> tuple[list[dict], list[dict]]:
    """Split `versions_introduced` output into (releasable, withheld) on whether the
    version has a changelog section.

    THIS REVERSES A DELIBERATE EARLIER POSITION, so it states why rather than quietly
    winning. `notes_for` in auto-release.yml carries the note "an unreleased version is
    a worse outcome than an under-documented one, so notes never block a release". That
    was right about NOTES and is wrong about EXISTENCE, and the difference is which
    failure the backstop already covers:

      - A documented version that fails to release is caught, loudly, by `--check` on
        this or any later push. It cannot go quiet.
      - An undocumented version that DOES release is caught by nothing, is public
        immediately, and is remediable only by hand. Both known instances proved it.

    So withholding is the safe side of an asymmetry, not a new risk: if a withheld
    version was real, documenting it makes `--check` demand it on the next push, and
    `--repair` can place it. The recovery path for a wrong withhold is automatic; the
    recovery path for a wrong release is a person deleting a tag.

    Note which versions this can actually withhold. `versions_introduced` has two
    passes: pass 1 reads plugin.json at each commit, pass 2 reads changelog sections.
    Pass-2 versions are documented BY CONSTRUCTION and can never be withheld here. The
    filter therefore bites only on pass-1 versions -- exactly the intermediate-commit
    class both incidents came from.
    """
    have = set(documented)
    releasable = [it for it in introduced if it["version"] in have]
    withheld = [it for it in introduced if it["version"] not in have]
    return releasable, withheld


def _git(*args: str) -> str:
    r = subprocess.run(("git", *args), capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def _version_at(commit: str) -> str | None:
    for path in (PLUGIN_JSON, LEGACY_PLUGIN_JSON):
        v = version_from_plugin_json(_git("show", f"{commit}:{path}"))
        if v:
            return v
    return None


def _changelog_at(commit: str) -> set[str]:
    """Documented versions in docs/changelog.md as of `commit`. Empty on any failure —
    a missing or unreadable changelog must not fail the release step; the gap check is
    the backstop for anything this misses."""
    try:
        return set(parse_changelog_versions(_git("show", f"{commit}:docs/changelog.md")))
    except Exception:  # noqa: BLE001 — unreadable history degrades, never blocks a release
        return set()


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

    # SECOND PASS: versions documented in the CHANGELOG but never visible in any
    # commit's plugin.json.
    #
    # plugin.json holds exactly ONE version, so the pass above sees one version per
    # commit. A SQUASH MERGE carrying two version bumps therefore yields one — the
    # last. That is what happened on 2026-08-05: v0.95.0 and v0.95.1 were squashed
    # into a single commit, plugin.json read 0.95.1, and v0.95.0 got no Release
    # despite a full changelog section promising one to consumers.
    #
    # This is the SAME defect the 2026-07-30 seven-version incident produced, one
    # layer in: that one was multiple versions across multiple COMMITS, fixed by
    # walking the range; this is multiple versions inside ONE commit, and walking
    # the range cannot see it. Both times the backstop caught what the primary
    # mechanism missed, which is the backstop working and the primary mechanism
    # still needing the fix — a gate that only ever passes because something behind
    # it catches the miss is not doing its job.
    #
    # The changelog is the right source because it is the CLAIM OF RECORD: if a
    # version has a section there, a consumer can reasonably expect a Release.
    # Anchored to the commit where the section first appears in the range.
    if not zeroish:
        base_documented = _changelog_at(before)
        floor_key = version_key(DEFAULT_FLOOR)
        for c in commits:
            fresh = _changelog_at(c) - base_documented
            for v in sorted(fresh, key=version_key):
                # Floor guard is load-bearing on a shallow or rewritten history: if
                # `before` has no readable changelog, `fresh` becomes EVERY documented
                # version, and without this the step would try to create 279 Releases.
                if v not in seen and version_key(v) >= floor_key:
                    seen[v] = c
                    out.append({"version": v, "commit": c})

    out.sort(key=lambda d: version_key(d["version"]))
    return out


def _rev_list(path: str) -> list[str]:
    """Commits touching `path`, oldest first. Only these can have changed a version."""
    return [c for c in _git("rev-list", "--reverse", "HEAD", "--", path).split("\n") if c]


def _anchor_by_plugin_json(want: set[str], commits: list[str], version_at) -> dict[str, str]:
    """Pass 1: the version is literally set in plugin.json. Mutates `want`, removing
    what it placed, so pass 2 only searches for what is still missing."""
    found: dict[str, str] = {}
    for c in commits:
        if not want:
            break
        v = version_at(c)
        if v in want:
            found[v] = c
            want.discard(v)
    return found


def _anchor_by_changelog(want: set[str], commits: list[str], changelog_at) -> dict[str, str]:
    """Pass 2: versions squashed into a commit whose plugin.json shows only the LAST
    of them are invisible to pass 1, but their changelog section still appears
    somewhere. Anchors to the commit where the section first shows up. Mutates `want`."""
    found: dict[str, str] = {}
    seen_doc: set[str] = set()
    for c in commits:
        if not want:
            break
        fresh = changelog_at(c) - seen_doc
        seen_doc |= fresh
        for v in sorted(fresh & want, key=version_key):
            found[v] = c
            want.discard(v)
    return found


def first_commit_for_versions(
    versions: set[str],
    plugin_commits: list[str] | None = None,
    changelog_commits: list[str] | None = None,
    version_at=_version_at,
    changelog_at=_changelog_at,
) -> dict[str, str]:
    """Map each wanted version to the commit where it FIRST appeared.

    The repair path needs this and `versions_introduced` cannot supply it: that
    function answers "what did THIS PUSH add", so a gap created by an outage, a
    failed job, or a force-push is invisible to it -- the version landed on a push
    that is long past. Repair has to search history instead of a range.

    Two passes, mirroring `versions_introduced` so both anchor identically:
      1. commits touching plugin.json -- the version is literally set there;
      2. commits touching the changelog -- for versions squashed into a commit whose
         plugin.json shows only the LAST of them (the 2026-08-05 v0.95.0 case).

    Only commits that touched the relevant file are walked, so this stays cheap even
    though it searches all of history rather than a range.

    Returns only versions it could locate. A version with no anchor is reported by the
    caller and never silently dropped -- a repair that quietly skips what it cannot
    place is the same fail-open this module exists to close.
    """
    want = set(versions)
    if not want:
        return {}

    if plugin_commits is None:
        plugin_commits = _rev_list(PLUGIN_JSON)
    found = _anchor_by_plugin_json(want, plugin_commits, version_at)

    if want:
        if changelog_commits is None:
            changelog_commits = _rev_list("docs/changelog.md")
        found.update(_anchor_by_changelog(want, changelog_commits, changelog_at))

    return found


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


def _cmd_repair(args) -> int:
    # The manual-dispatch path. `--introduced` cannot serve it: on a
    # workflow_dispatch `github.event.before` is empty, so the range degrades to
    # HEAD alone and yields the ONE version already at the tip -- which is
    # invariably the version that already has a Release. That is why the
    # documented "manual re-run repairs gaps" promise did not hold: on 2026-08-07
    # a GitHub outage left v0.100.0 and v0.101.0 unreleased, and a dispatch would
    # have re-offered v0.101.1 and repaired neither. Repair must ask "what is
    # missing", not "what is new".
    with open(args.changelog) as fh:
        documented = parse_changelog_versions(fh.read())
    gaps = missing_releases(documented, _released_from_gh(), args.floor)
    anchors = first_commit_for_versions(set(gaps))
    unlocatable = [g for g in gaps if g not in anchors]
    if unlocatable:
        # Loud, and non-zero. A repair that silently emits a shorter list than the
        # gap it was asked to close is the fail-open this module exists to close.
        print("::error::no originating commit found for: "
              + ", ".join("v" + u for u in unlocatable), file=sys.stderr)
        print(json.dumps([{"version": v, "commit": anchors[v]} for v in gaps
                          if v in anchors]))
        return 1
    print(json.dumps([{"version": v, "commit": anchors[v]} for v in gaps]))
    return 0


def _cmd_audit(args) -> int:
    # DELIBERATELY NOT A STEP IN auto-release.yml. It can only ever fire AFTER a
    # Release is public, so as a release-time gate it would add a fourth way to
    # redden main while preventing nothing -- the enumeration gate above is what
    # prevents. Its value is finding what is ALREADY wrong: run it on a schedule.
    # It is the only thing that would ever have surfaced v0.107.1, undocumented
    # and unnoticed for 27 days.
    with open(args.changelog) as fh:
        documented = parse_changelog_versions(fh.read())
    strays = undocumented_releases(_released_from_gh(), documented, args.floor)
    if strays:
        print(f"::error::{len(strays)} Release(s) have no changelog section: "
              + ", ".join("v" + s_ for s_ in strays))
        print("A Release is a public claim that a version shipped. Either document "
              "these in docs/changelog.md or delete them.", file=sys.stderr)
        return 1
    print(f"OK: every Release >= v{args.floor} has a changelog section.")
    return 0


def _cmd_check(args) -> int:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--introduced", nargs=2, metavar=("BEFORE", "HEAD"),
                    help="print JSON [{version, commit}] introduced by BEFORE..HEAD")
    ap.add_argument("--require-documented", action="store_true",
                    help="with --introduced: withhold any version that has no changelog "
                         "section, and report what was withheld. Prevents the "
                         "intermediate-commit phantom release (v0.176.0, v0.107.1).")
    ap.add_argument("--audit", action="store_true",
                    help="exit 1 if any Release at/above the floor has no changelog "
                         "section. The mirror of --check. NOT wired into the release "
                         "job: see the note in the handler.")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any changelog version at/above the floor has no Release")
    ap.add_argument("--repair", action="store_true",
                    help="print JSON [{version, commit}] for every documented version that "
                         "has no Release, anchored to the commit it first appeared in")
    ap.add_argument("--changelog", default="docs/changelog.md")
    ap.add_argument("--floor", default=DEFAULT_FLOOR)
    args = ap.parse_args()

    if args.introduced:
        items = versions_introduced(*args.introduced)
        if args.require_documented:
            with open(args.changelog) as fh:
                documented = parse_changelog_versions(fh.read())
            items, withheld = partition_undocumented(items, documented)
            for it in withheld:
                # A WARNING, NOT AN ERROR, AND THE DISTINCTION IS THE WHOLE DESIGN.
                # Failing here would redden main on a push whose real work landed,
                # which trains the "it is fine, the release went out" dismissal this
                # workflow already has one instance of. Nothing is silently wrong
                # when a withhold fires: the bad artifact simply is not created, and
                # the fix (write the changelog section) makes the next push release
                # it. This is the opposite shape from "absence produced a success" --
                # here presence is what is being prevented.
                print(f"::warning::withholding v{it['version']}: no `## v{it['version']}` "
                      f"section in {args.changelog}. A version that appears only in an "
                      f"intermediate commit is not a release. Document it to ship it.")
        print(json.dumps(items))
        return 0

    if args.repair:
        return _cmd_repair(args)

    if args.audit:
        return _cmd_audit(args)

    if args.check:
        return _cmd_check(args)

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
