#!/usr/bin/env python3
"""check_cycle_recording.py — catch framework work that shipped without a cycle record.

THE DEFECT THIS EXISTS FOR (found in dogfood 2026-08-06):

    `engine/cycle-learning.md#when-to-record` listed four triggers, ALL of them
    keyed to the leaf lifecycle (leaf archived, leaf launched, post-launch
    review, rework follow-up). None matches framework-self-development.

    The only place in the whole codebase that opens a `meta-dogfood` cycle is
    `skills/diamond-progress/SKILL.md` — and it fires at a DIAMOND PHASE
    TRANSITION. Framework work does not move diamonds through phases. It ships
    releases.

    So framework work was recordable in principle and unrecordable in practice.

Measured consequence in the dogfood project: 48 minor releases across 49 days
(2026-06-18 -> 2026-08-06) — two validator checks, two engine layers, three
skills, four guards — with zero diamond phase transitions, therefore zero
triggers, therefore zero cycles. Nine of its twelve prior cycles had landed in
one 19-day window while the cycle machinery was itself being built. The ledger
was tracking ATTENTION, not work, and nothing could tell the difference between
"no cycle was owed" and "a cycle was owed and nobody noticed" — anti-pattern #9
(Fail-Open on Absent Input) applied to the learning ledger itself.

WHAT IT CHECKS
    How many MINOR releases (vX.Y.0) shipped since the newest `completed_at`
    in `cycle-history.yml`. At or above the threshold, a `meta-dogfood` cycle
    is owed and this fails loud.

    Minor, not patch, deliberately. A patch is maintenance, and the 2026-06-18
    ruling that steady-state ops earns no cycle still stands.

WHAT IT DELIBERATELY DOES NOT DO
    It does not write the record, and it does not guess where the arc begins
    or ends. Both are judgements. A script that guessed would have to invent
    the effort estimate — which is the ONE required calibration field on a
    meta-dogfood record (see the narrowed Framework-on-Framework Exemption),
    so a guessed arc would fabricate the only number the record exists to
    carry. It asserts the arc was CONSIDERED, the same shape as
    `check_bvssh_reconcile.py`.

    It is also not satisfiable by touching the file: the pass condition is a
    cycle whose `completed_at` is newer than the releases, not a modification
    timestamp. Editing `cycle-history.yml` without adding a cycle changes
    nothing here. That is on purpose — a check whose cheapest green is a
    whitespace commit belongs to the blind-green family it was built against.

ABSENT-INPUT DISCIPLINE (anti-pattern #9 — fail loud, but only on real gaps)
    - Not a git repo, or git unavailable      -> exit 2, LOUD. "I could not
      look" must never render as "nothing to report".
    - No `cycle-history.yml`                   -> exit 0. A project that has
      never recorded a cycle is not in violation; it has not started.
    - No release commits found at all          -> exit 0, and SAY SO with the
      `no-releases-matched` token. This is the branch most likely to be a
      broken pattern rather than a true absence, so it prints the pattern it
      used and the number of commits it scanned. Silence here would reproduce
      the exact defect the check is named for.
    - Cycles exist, releases exist, arc short  -> exit 0 with the count.
    - Arc at or over threshold                 -> exit 1.

Usage:
    check_cycle_recording.py [--project-dir DIR] [--threshold N]
                             [--release-pattern REGEX] [--json]

Exit codes:
    0 — no cycle owed (or nothing to assess)
    1 — a meta-dogfood cycle is owed
    2 — argument/input error, or the probe could not run

Python stdlib + PyYAML (already a framework dependency).
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared framework-wide
    print("check_cycle_recording: PyYAML is required", file=sys.stderr)
    sys.exit(2)

DEFAULT_THRESHOLD = 5

# Cap on release tokens printed inline. The full set is always available via
# --json; a wall of 48 versions in a reminder is noise, not evidence.
MAX_RELEASES_SHOWN = 12

# Matches a minor release token anywhere in a commit subject, e.g. "v0.97.0".
# Anchored on a non-word boundary rather than start-of-string because one
# commit can announce two releases — "v0.95.0 + v0.95.1: ..." is real history,
# and upstream v0.95.2 exists BECAUSE an earlier step read only the first.
MINOR_RELEASE_RE = re.compile(r"\bv(\d+)\.(\d+)\.0\b")


def _git(project_dir: Path, *args: str) -> str:
    """Run git, raising RuntimeError on failure rather than returning ''.

    An empty string from a failed git call is indistinguishable from a
    repository with no matching commits. That conflation is the whole class
    this script exists to catch, so it must not appear in the script itself.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,  # returncode inspected below; a raise here would lose stderr
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git executable not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("git call timed out after 30s") from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}): "
            f"{result.stderr.strip() or '<no stderr>'}"
        )
    return result.stdout


def newest_cycle_completion(cycle_file: Path):
    """Return (iso_date_string, cycle_id) of the newest completed cycle, or None."""
    try:
        data = yaml.safe_load(cycle_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"could not parse {cycle_file.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError(f"{cycle_file.name} did not parse to a mapping")

    cycles = data.get("cycles")
    if not isinstance(cycles, list):
        return None

    newest = None
    for entry in cycles:
        if not isinstance(entry, dict):
            continue
        completed = entry.get("completed_at")
        if completed is None:
            continue
        # PyYAML may hand back a date/datetime for an unquoted timestamp.
        stamp = completed if isinstance(completed, str) else str(completed)
        stamp = stamp.strip()
        if not stamp:
            continue
        if newest is None or stamp > newest[0]:
            # `cycle_id` is the schema's field name; `id` accepted as a fallback
            # so a hand-written record does not silently label itself <unnamed>.
            ident = entry.get("cycle_id") or entry.get("id") or "<unnamed>"
            newest = (stamp, str(ident))
    return newest


def minor_releases_since(project_dir: Path, since_iso, pattern: re.Pattern):
    """Return (releases, commits_scanned). `since_iso` None means whole history."""
    args = ["log", "--format=%s"]
    if since_iso:
        args.append(f"--since={since_iso}")
    subjects = [line for line in _git(project_dir, *args).splitlines() if line.strip()]

    releases = []
    for subject in subjects:
        releases.extend(match.group(0) for match in pattern.finditer(subject))
    return releases, len(subjects)


def load_threshold(project_dir: Path, override):
    """Threshold precedence: CLI override > thresholds.yml > module default."""
    if override is not None:
        return override, "--threshold"

    path = project_dir / ".claude" / "canvas" / "thresholds.yml"
    if not path.is_file():
        return DEFAULT_THRESHOLD, "default (no thresholds.yml)"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        # A malformed thresholds file is a real problem, but it belongs to
        # validate_canvas.py. Fall back visibly rather than crashing here.
        return DEFAULT_THRESHOLD, "default (thresholds.yml unreadable)"

    entry = (data.get("thresholds") or {}).get("cycle_recording_arc")
    if isinstance(entry, dict):
        for key, label in (("calibrated", "calibrated"), ("default", "declared default")):
            value = entry.get(key)
            if isinstance(value, int) and value > 0:
                return value, f"thresholds.yml#cycle_recording_arc.{key} ({label})"
    return DEFAULT_THRESHOLD, "default (cycle_recording_arc unset)"


def _report_no_matches(as_json, commits_scanned, since_label, pattern) -> int:
    """The branch most likely to be a broken pattern rather than a true absence.

    It gets a distinct token and shows its working, because an empty result that
    means both "none" and "never matched" is the exact defect this file is named for.
    """
    detail = (
        f"no-releases-matched — 0 minor releases in {commits_scanned} commit subject(s) "
        f"since {since_label}; pattern was {pattern.pattern!r}"
    )
    if as_json:
        # STATUS IS ITS OWN TOKEN, NOT "ok" (2026-08-16). This branch means "the
        # check could not measure here", which is a different state from "measured
        # and found nothing owed". Folding it into "ok" made the honesty above
        # unreachable: session-start.sh reacts only to named statuses, so a project
        # whose releases ship from a DIFFERENT repo got silence from a check that had
        # correctly reported it could not see them. Measured in the dogfood repo the
        # same day: two minor releases shipped upstream, this returned ok/0.
        print(json.dumps({"status": "no-releases-matched", "releases": 0, "detail": detail}))
    else:
        print(f"check_cycle_recording: OK — {detail}")
    return 0


def _report_never_recorded(as_json, releases, commits_scanned, threshold, threshold_source) -> int:
    """NEVER-RECORDED is its own state, not a very wide arc.

    Without this branch the framework repo — 86 minor releases, zero cycles — is
    told it owes ONE cycle spanning its entire history. That demand cannot be met,
    and a check that opens with an unmeetable demand gets muted, which leaves it
    decorative: the same end state as the drift it was built to stop, reached by a
    different route. So it still exits 1 (framework work HAS shipped unrecorded,
    and saying otherwise would be the fail-open this file argues against), but asks
    for the one step actually available. The release total is context, not the size
    of the demand.
    """
    count = len(releases)
    if as_json:
        print(json.dumps({
            "status": "never-recorded",
            "releases": count,
            "threshold": threshold,
            "threshold_source": threshold_source,
            "commits_scanned": commits_scanned,
        }, indent=2))
    else:
        print(
            f"check_cycle_recording: FAIL — never-recorded — {count} minor release(s) on "
            f"record and no completed cycle. This is a baseline gap, NOT an arc {count} "
            f"releases wide.\n"
            f"  Record ONE `meta-dogfood` cycle to establish the baseline, bounding its arc\n"
            f"  where you judge the arc to be. Every later run measures from that cycle's\n"
            f"  completed_at, so this is a one-time step, not a backlog of {count}.\n"
            f"  Run /mycelium:retrospective."
        )
    return 1


def report(scan: dict, *, as_json: bool) -> int:
    """Render the verdict and return the exit code.

    Takes the scan result as one mapping rather than eight parameters — the
    fields travel together and always have.
    """
    releases = scan["releases"]
    commits_scanned = scan["commits_scanned"]
    newest = scan["newest"]
    since_label = scan["since_label"]
    pattern = scan["pattern"]
    threshold = scan["threshold"]
    threshold_source = scan["threshold_source"]

    if not releases:
        return _report_no_matches(as_json, commits_scanned, since_label, pattern)
    if newest is None:
        return _report_never_recorded(
            as_json, releases, commits_scanned, threshold, threshold_source
        )

    distinct = sorted(set(releases))
    owed = len(releases) >= threshold

    if as_json:
        print(json.dumps({
            "status": "cycle-owed" if owed else "ok",
            "releases": len(releases),
            "threshold": threshold,
            "threshold_source": threshold_source,
            "since": since_label,
            "release_tokens": distinct,
            "commits_scanned": commits_scanned,
        }, indent=2))
    elif owed:
        extra = len(distinct) - MAX_RELEASES_SHOWN
        shown = ", ".join(distinct[:MAX_RELEASES_SHOWN])
        if extra > 0:
            shown += f" (+{extra} more)"
        print(
            f"check_cycle_recording: FAIL — {len(releases)} minor releases since "
            f"{since_label}, threshold {threshold} ({threshold_source}).\n"
            f"  A `meta-dogfood` cycle is owed. Run /mycelium:retrospective to record it.\n"
            f"  Releases: {shown}\n"
            f"  This check does NOT write the record — where the arc begins and ends is a\n"
            f"  judgement, and the effort estimate is the one calibration field it must carry."
        )
    else:
        print(
            f"check_cycle_recording: OK — {len(releases)} minor release(s) since "
            f"{since_label}, under threshold {threshold} ({threshold_source})."
        )

    return 1 if owed else 0


# ---------------------------------------------------------------------------
# FIELD COVERAGE (v0.121.0) — SEPARATE FROM THE RELEASE-CADENCE CHECK ABOVE.
#
# This function shares a file with the cadence scan and shares NOTHING else: no
# threshold, no release counting, no git history. That separation is deliberate and
# was requested. The cadence half asks "has a cycle been recorded lately", keyed on
# minor releases, and its unit is contested — wiring it while the unit is wrong would
# ship a green CI row over a stale log. Coverage asks a different question with no
# threshold to get wrong: OF THE CYCLES THAT EXIST, how many carry the fields the spec
# says feed /framework-health?
#
# WHY IT IS WARN-ONLY AND NEVER FAILS. Measured on the dogfood repo 2026-08-23:
# gates_fired and regressions appeared on ZERO of sixteen records. Failing on that
# would break every project that has ever run /retrospective, and a check that is
# noisy from the first run gets muted.
#
# THE 14-DAY RULE ON REWORK IS NOT A COURTESY. `rework` is populated fourteen days
# after completion by design. Counting a cycle that closed on Tuesday as missing it
# would alarm on evidence that could not exist yet — the failure this project logged
# as "absence is only a finding once it could have been filled". So recent cycles are
# excluded from the rework denominator and the exclusion is reported, not hidden.
REWORK_WINDOW_DAYS = 14


def _observed_only(closed):
    """Drop records reconstructed after the fact.

    SAME PRINCIPLE AS THE 14-DAY REWORK LAG BELOW: do not alarm on evidence that cannot exist.
    A `reconstructed_post_hoc` record is a backfill of work that shipped before the trigger
    existed, so nobody was watching which gates fired or whether a regression followed. Those
    observations were never made and cannot be recovered; writing `gates_fired: []` would not
    record a measurement, it would add a fabricated zero to framework-health's denominator and
    deflate measured gate effectiveness.

    DERIVED, NOT INVENTED. engine/cycle-learning.md already exempts reconstructed records from
    every calibration aggregate, for the stated reason that "a reconstructed estimate is a number
    invented today to grade work done months ago". Extending that to the two observational fields
    is this file applying the doc's own reasoning; the doc records the extension explicitly.
    The precedent is exact: v0.98.1 exists because a rule shipped and instantly created three
    violating reconstructed rows, and this is the same three rows meeting a different rule.

    `demand_type` IS NOT EXEMPT and is deliberately excluded from this filter. Seddon's type
    classifies WHY work was asked for, not what was observed while it ran, and that stays
    determinable from the record long afterwards.
    """
    return [c for c in closed if not c.get("reconstructed_post_hoc")]


def _missing_field_finding(closed, field, feeds, excluded=0):
    """One coverage line for a spec field, or None when every cycle carries it."""
    absent = [c.get("cycle_id", "?") for c in closed if field not in c]
    if not absent:
        return None
    note = (f" {excluded} reconstructed record(s) are excluded from this count: the observation "
            f"was never made and cannot be recovered." if excluded else "")
    return (
        f"{len(absent)} of {len(closed)} closed cycles carry no `{field}` "
        f"(feeds {feeds}). An empty list or zero is a measurement; an absent "
        f"field is not. Oldest affected: {absent[0]}, newest: {absent[-1]}.{note}"
    )


def _rework_finding(closed, today):
    """Rework coverage, measured ONLY on cycles old enough to have it.

    `rework` is populated on a 14-day lag by design, so counting a cycle that closed
    on Tuesday as missing it would alarm on evidence that cannot exist yet.
    """
    eligible, undated = [], 0
    for c in closed:
        try:
            done = datetime.date.fromisoformat(str(c.get("completed_at") or "")[:10])
        except ValueError:
            undated += 1
            continue
        if (today - done).days >= REWORK_WINDOW_DAYS:
            eligible.append(c)
    missing = [c.get("cycle_id", "?") for c in eligible if "rework" not in c]
    if not missing:
        return None
    note = f" ({undated} cycle(s) skipped: unreadable completed_at)" if undated else ""
    return (
        f"{len(missing)} of {len(eligible)} cycles closed more than "
        f"{REWORK_WINDOW_DAYS} days ago carry no `rework` block{note}. Cycles closed "
        f"more recently are excluded — the field is populated on a {REWORK_WINDOW_DAYS}-day "
        f"lag by design, and flagging them would alarm on evidence that cannot exist yet."
    )


def cycle_field_coverage(cycle_file, today=None):
    """WARN-tier findings about spec fields the recorded cycles do not carry.

    Returns a list of human-readable strings; empty when coverage is complete or when
    there is nothing to measure. Never raises on a malformed file: a coverage report
    that breaks the validator is worse than one with a gap.
    """
    try:
        data = yaml.safe_load(cycle_file.read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return []
    cycles = data.get("cycles") if isinstance(data, dict) else None
    if not isinstance(cycles, list):
        return []

    closed = [c for c in cycles
              if isinstance(c, dict) and c.get("terminal_state") != "in_flight"]
    if not closed:
        return []

    if today is None:
        today = datetime.datetime.now(datetime.UTC).date()

    # Observational fields are measured only on records where someone was actually watching.
    observed = _observed_only(closed)
    dropped = len(closed) - len(observed)

    findings = [
        _missing_field_finding(observed, "gates_fired",
                               "/mycelium:framework-health Gate effectiveness", dropped),
        _missing_field_finding(observed, "regressions",
                               "/mycelium:framework-health Regression rate", dropped),
        # Added v0.130.0. demand_type shipped in v0.129.0 WITH its consumer, which was the
        # fix for gates_fired's producer-without-reader defect — but it shipped without the
        # absence WARN its two siblings above have, so a missing demand_type was SILENT where
        # theirs are noisy. A field that is only quiet when unpopulated is how 0-of-16
        # compliance goes unnoticed for months.
        _missing_field_finding(closed, "demand_type",
                               "/mycelium:framework-health Demand mix"),
        _rework_finding(observed, today),
    ]
    return [f for f in findings if f]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when framework releases have accumulated with no meta-dogfood cycle."
    )
    parser.add_argument(
        "--project-dir", "--root", dest="project_dir", default=".",
        help=(
            "project root holding .claude/canvas (default: cwd). `--root` is an alias so "
            "check_empty_input_honesty.py can aim this at an empty tree; without it the "
            "guard reports this script as untestable, and its empty-input behaviour would "
            "go unverified -- which is the anti-pattern #9 shape one level up."
        ),
    )
    parser.add_argument(
        "--release-repo",
        default=None,
        help=(
            "repo whose release history counts (default: --project-dir). Set this when the "
            "cycle ledger and the framework work live in DIFFERENT repos — a dogfood consumer "
            "installs the plugin and records cycles locally while the releases ship upstream."
        ),
    )
    parser.add_argument(
        "--threshold", type=int, default=None,
        help="minor releases before a cycle is owed",
    )
    parser.add_argument("--release-pattern", default=None, help="override the minor-release regex")
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"check_cycle_recording: not a directory: {project_dir}", file=sys.stderr)
        return 2

    release_repo = Path(args.release_repo).resolve() if args.release_repo else project_dir
    if not release_repo.is_dir():
        print(
            f"check_cycle_recording: --release-repo is not a directory: {release_repo}",
            file=sys.stderr,
        )
        return 2

    pattern = MINOR_RELEASE_RE
    if args.release_pattern:
        try:
            pattern = re.compile(args.release_pattern)
        except re.error as exc:
            print(f"check_cycle_recording: bad --release-pattern: {exc}", file=sys.stderr)
            return 2

    threshold, threshold_source = load_threshold(project_dir, args.threshold)

    cycle_file = project_dir / ".claude" / "canvas" / "cycle-history.yml"
    if not cycle_file.is_file():
        # PRECONDITION FAILURE (exit 2), not a pass.
        #
        # A fresh project genuinely may have no ledger, so the first version
        # returned 0 here and called it an honest skip. check_empty_input_honesty.py
        # rejected that, and it is right for a reason worth keeping: exit 0 asserts
        # "I looked and everything is fine", which is false when nothing was looked
        # at. Exit 2 says "I could not assess", which is what actually happened.
        #
        # Safe to do: this script is ADVISORY via session-start, which reads --json
        # and reacts only to named statuses, so the exit code changes no consumer
        # behaviour. It is not a CI gate and cannot redden a fresh project's build.
        msg = (
            f"cannot assess: no {cycle_file.relative_to(project_dir)} under {project_dir}. "
            f"A project that has never recorded a cycle has no baseline to measure an arc "
            f"from. NOTHING WAS ASSESSED — this is not a pass."
        )
        if args.json:
            print(json.dumps({"status": "precondition-failed", "reason": msg}))
        else:
            print(f"check_cycle_recording: ERROR — {msg}", file=sys.stderr)
        return 2

    try:
        newest = newest_cycle_completion(cycle_file)
        releases, commits_scanned = minor_releases_since(
            release_repo, newest[0] if newest else None, pattern
        )
    except (RuntimeError, TypeError) as exc:
        # LOUD. "I could not look" must never be reported as "nothing found".
        print(f"check_cycle_recording: ERROR — {exc}", file=sys.stderr)
        return 2

    since_label = (
        f"{newest[1]} completed {newest[0]}" if newest
        else "the start of history (no completed cycle on record)"
    )
    # Always disclose which repo supplied the releases. Scanning the wrong repo
    # produces a plausible number rather than an error — the roadmap repo mentions
    # 10 upstream versions in its own commit subjects while 29 actually shipped —
    # so the count must never appear without saying where it came from.
    if release_repo != project_dir:
        since_label += f" [releases counted in {release_repo}]"

    return report(
        {
            "releases": releases,
            "commits_scanned": commits_scanned,
            "newest": newest,
            "since_label": since_label,
            "pattern": pattern,
            "threshold": threshold,
            "threshold_source": threshold_source,
        },
        as_json=args.json,
    )


if __name__ == "__main__":
    sys.exit(main())
