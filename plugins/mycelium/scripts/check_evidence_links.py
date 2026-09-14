#!/usr/bin/env python3
"""Find citations anywhere in a project that no longer resolve.

SHIPPED UPSTREAM 0.205.0 from the dogfood project's auto-dogfood tree, where it ran from
2026-08-17. Paths resolve from --project-dir (default: the working directory); the snapshot
store and the browser-verdict file live under the project's .claude/evals/metrics/evidence-links/.

WHY THIS EXISTS. On 2026-08-17 the first full competitor sweep probed 39 landscape
URLs and four returned 404. Every one was an article, and NONE of them were dead:
one slug had changed, one article had been RETITLED, one had moved to a different
publisher, and one had been cited to a secondary outlet for a piece that lives on
the author's own site. The canvas had been carrying four claims whose sources
nobody could open, and two of them under the wrong title. Nothing was watching.

This project's own rule is that you may not assert an absence you have not
searched. A citation that 404s is the same defect one layer down: a claim whose
evidence can no longer be checked by anyone, including the person who wrote it.

WHAT IT IS NOT. It is NOT competitor monitoring, and the two must never share a
report. A competitor going dormant is a fact about a product; a 404 is usually a
fact about a CMS. Reporting them together tells you a rival died when a magazine
reorganised its site — which is precisely the confusion that made this check worth
building separately.

THREE DESIGN RULES, EACH FROM A FAILURE THIS PROJECT HAS ALREADY HAD:

  1. A FAILED PROBE IS NOT A ROTTED LINK. 429, 5xx, timeouts, DNS and TLS errors
     mean WE could not look. They report UNKNOWN and never ROT. The archive.org
     chase on 2026-08-17 returned 502/503 across the board, and reading that as
     "no snapshot exists" would have been a fabricated absence.
  2. 401/403 IS A BOT WALL, NOT A DEAD PAGE. LinkedIn, X and friends refuse
     robots by policy. Their content is fine and a human can open it.
  3. TWO STRIKES BEFORE ROT. A single 404 can be a deploy blip or an edge-cache
     miss. First failure records PENDING; only a second consecutive failing run
     escalates to ROTTED. This is the day-one-wolf guard: a check that cries on
     the first transient failure gets muted, and a muted check looks like
     coverage.

SELF-THROTTLING. ~390 external requests is rude on every push and pointless daily.
The run no-ops unless the newest snapshot is older than --max-age-days, so it can
sit on a per-push hook and still only really run every couple of weeks.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

HTTP_GONE = (404, 410)          # the page is claimed absent
HTTP_BOT_WALL = (401, 403)      # the SITE refuses robots; says nothing about the page
HTTP_NOT_FOUND = 404
MIN_REPO_PATH_PARTS = 2         # owner/repo — anything shorter is not a repo path
PENDING_SHOWN = 10              # a first-strike list is a preview, not the record
ALLOWED_SCHEMES = ("http://", "https://")

OK = "ok"
ROTTED = "ROTTED"
PENDING = "pending"
BLOCKED = "blocked"
UNKNOWN = "unknown"

# Backtick excluded and stripped: markdown code spans (`https://x/`) were producing
# URLs with a trailing backtick that 404 while the real link is fine. Both
# "pending" findings of the first widened run were that artifact, not rot.
URL_RE = re.compile(r'https?://[^\s"\'<>)\],;`]+')

# WIDENED 2026-08-17. The first version read `.claude/canvas/*.yml` only — 216 URLs of
# the 397 in the repo. Asked whether we now knew there was no link rot, the honest
# answer was no, and the largest reason was coverage: `docs/` alone holds 136 cited
# URLs and is the PUBLIC-facing surface, where a dead citation is most visible and
# least excusable. Narrow coverage reporting green is the "looks like coverage"
# failure this project keeps finding, so the roots are now explicit and listed.
SEARCH_ROOTS = [
    (".claude/canvas", "*.yml"),
    (".claude/diamonds", "*.yml"),
    (".claude/harness", "*.md"),
    (".claude/memory", "*.md"),
    (".claude/evals", "**/*.md"),
    (".claude/evals", "**/*.yml"),
    ("docs", "**/*.md"),
]
SNAP_REL = pathlib.Path(".claude/evals/metrics/evidence-links")
UA = "Mozilla/5.0 (compatible; mycelium-linkcheck/1; +https://github.com/haabe/mycelium)"

#: The project root every path below resolves against. Set once by main() from --project-dir;
#: module-level so the helpers keep their signatures and the tests can point it at a tmp tree.
ROOT = pathlib.Path(".")


def snap_dir() -> pathlib.Path:
    return ROOT / SNAP_REL


def verified_file() -> pathlib.Path:
    return snap_dir() / "browser-verified.json"

# Bot-walled URLs are the one class this script CANNOT settle. A 403 from LinkedIn,
# Medium or a Cloudflare-fronted blog says the site refuses robots — it says nothing
# about whether the page is still there, which is the question the canvas needs
# answered. A logged-in browser can answer it; urllib never will.
#
# So the script ASKS for a browser check instead of guessing, and records the answer
# here so it stops asking. Without this file the request would repeat every session
# forever, which is the muted-check failure this whole check exists to avoid: a nudge
# that always says the same thing gets skimmed, and a skimmed nudge is not coverage.


def load_verified() -> dict:
    """Browser verdicts. A corrupt store is REPORTED, not silently emptied.

    Returning {} on a parse error looks harmless — the check just asks for the
    browser again — but it silently discards every human verdict ever recorded and
    the report reads as if none had been given. Absence laundered into a default,
    which is the anti-pattern this file guards against everywhere else.
    """
    vf = verified_file()
    if not vf.exists():
        return {}
    try:
        return json.loads(vf.read_text())
    except (OSError, ValueError) as e:
        print(f"  WARNING: {vf.name} is unreadable ({type(e).__name__}). Every "
              f"browser verdict is being ignored this run, so URLs already checked by a "
              f"human will be asked for again. Fix the file rather than re-verifying.",
              file=sys.stderr)
        return {}


def mark_verified(url: str, verdict: str, note: str, today: datetime.date) -> None:
    """Record a human/browser verdict for a URL urllib cannot reach."""
    data = load_verified()
    data[url] = {"verdict": verdict, "checked_at": str(today), "note": note,
                 "method": "browser"}
    vf = verified_file()
    vf.parent.mkdir(parents=True, exist_ok=True)
    vf.write_text(json.dumps(data, indent=1, sort_keys=True))


# RFC 2606 / RFC 6761 reserve these for documentation. A URL on one of them is an
# ILLUSTRATION, never evidence, and probing it produces a 404 that looks exactly
# like a rotted citation. The first run of this check reported
# https://example.com/market-report as pending rot; it sits in a COMMENT in
# landscape.yml demonstrating the evidence_sources format. Skipping them by domain
# rather than by "is it in a comment" is deliberate — plenty of real citations in
# this canvas do live in comment prose, so filtering comments would hide evidence.
RESERVED = ("example.com", "example.net", "example.org",
            "example.edu", ".example", ".test", ".invalid", ".localhost")

# THE FRAMEWORK'S OWN CITATIONS ARE NOT THE CONSUMER'S TO CHECK.
#
# A shipped version of this script must scan the PROJECT's surfaces and never the
# plugin's own files. A consumer who finds a dead link in a Mycelium skill doc cannot
# fix it, did not write it, and would see the identical finding as every other
# consumer — N projects reporting one upstream defect, in a report about THEIR canvas.
# That is noise in the one place a health report has to stay readable.
#
# The framework's ~50 citations are this repo's job, because surfacing friction back
# upstream is what a dogfood project is for. Hence --include-framework, which is opt-in
# and points at the framework tree rather than the project.
FRAMEWORK_GLOBS = ["**/*.md"]


# API ENDPOINTS ARE NOT CITATIONS, AND THIS IS NOT COSMETIC.
# Widening to docs/ pulled in adapter documentation full of endpoint examples —
# api.stripe.com/v1/charges, api.intercom.io, api.eu.intercom.io. They return 401/403
# because they want an API KEY, which the classifier read as "bot wall — a human can
# open this" and put on the browser-ask list. It grew to THIRTY entries, and asking a
# human to open a Stripe endpoint in Chrome is nonsense that would teach the reader to
# ignore the whole list. No claim rests on these; they document how to call something.
API_HOST = re.compile(r"^api[.-]|\.api\.", re.IGNORECASE)


def _assert_http(url: str) -> None:
    """Refuse every scheme but http(s).

    S310 is not pedantry here: these URLs come out of repo FILES. `URL_RE` only
    matches http(s) today, so a `file:` read is currently unreachable — but that
    proof lives in a regex 200 lines away, and widening the regex would make it
    reachable with no other signal. The check belongs at the call.
    """
    if not url.lower().startswith(ALLOWED_SCHEMES):
        msg = f"refusing a non-http(s) scheme: {url}"
        raise ValueError(msg)


def _request(url: str, headers: dict[str, str], method: str = "GET") -> urllib.request.Request:
    _assert_http(url)
    return urllib.request.Request(url, headers=headers, method=method)  # noqa: S310 - guarded


def _urlopen(req: urllib.request.Request, timeout: int):
    _assert_http(req.full_url)
    return urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 - guarded


def is_api_endpoint(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    return bool(API_HOST.search(host))


def is_placeholder(url: str) -> bool:
    # A URL carrying an unexpanded variable is a TEMPLATE, not a citation. The widened
    # run surfaced `https://api.appstoreconnect.apple.com/v1/apps/$APPSTORE_APP_ID`
    # from a docs example and asked for a browser check on it. Same class as the
    # RFC 2606 domains: an illustration of a URL, not a claim about a page.
    if any(t in url for t in ("$", "{", "<", "YOUR_", "OWNER/REPO")):
        return True
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    return any(host == r or host.endswith(r) for r in RESERVED)


def _clean(text: str, m: re.Match) -> str:
    """Trim delimiters the surrounding markup owns, not the URL.

    A trailing underscore cannot be blanket-stripped the way a backtick can, because
    `_` is legal in a URL path. So it is only removed when the character immediately
    BEFORE the match is also `_` — i.e. the URL sits inside matched markdown emphasis
    and the trailing one is the closing delimiter. Found 2026-08-17: the framework
    scan's single finding was `.../handoff.md_` from `_Produced with Mycelium ... md_`
    in receipt-render/SKILL.md. The real URL returns 200; the underscore was mine.
    """
    u = m.group(0).rstrip(".,)`'\"")
    # A URL inside a double-quoted YAML scalar can drag the scalar's escape sequence along:
    # `"...github.com/haabe/mycelium\n"` yielded a URL ending in a literal backslash-n, which
    # 404s while the real page is fine (first upstream run, 2026-09-14). Escapes are markup.
    while u.endswith(("\\n", "\\t", "\\r")):
        u = u[:-2]
    if u.endswith("_"):
        line_start = text.rfind("\n", 0, m.start()) + 1
        if "_" in text[line_start:m.start()]:
            u = u[:-1]
    return u

def _citations_in(path: pathlib.Path) -> collections.abc.Iterator[str]:
    """Every URL in one file that is a CITATION rather than an illustration.

    The two filters are not cosmetic and each has a receipt in the comments above:
    a reserved domain is an example of a URL, and an api.* host wants a key rather
    than a reader. Both produce a 404 indistinguishable from real rot.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    for m in URL_RE.finditer(text):
        u = _clean(text, m)
        if not (is_placeholder(u) or is_api_endpoint(u)):
            yield u


def collect(framework_root: pathlib.Path | None = None) -> dict[str, list[str]]:
    """url -> the repo-relative files that cite it.

    Repo-relative and not just the basename, because with seven roots there are now
    several files called the same thing and "cited by 2026-08-17.md" would send a
    reader hunting.
    """
    cited: dict[str, set[str]] = collections.defaultdict(set)

    def harvest(paths: collections.abc.Iterable[pathlib.Path], label) -> None:
        for p in paths:
            if not p.is_file():
                continue
            for u in _citations_in(p):
                cited[u].add(label(p))

    for rel, pattern in SEARCH_ROOTS:
        root = ROOT / rel
        if root.exists():
            harvest(sorted(root.glob(pattern)), lambda p: str(p.relative_to(ROOT)))

    if framework_root is not None:
        # Tagged `framework:` in cited_by so a reader can tell at a glance that a
        # finding is OURS TO FILE UPSTREAM rather than ours to fix in canvas.
        for pattern in FRAMEWORK_GLOBS:
            harvest(
                (p for p in sorted(framework_root.glob(pattern))
                 if ".git" not in p.parts and "node_modules" not in p.parts),
                lambda p: f"framework:{p.relative_to(framework_root)}",
            )

    return {u: sorted(f) for u, f in cited.items()}


# GITHUB ANSWERS ROBOTS WITH 404, NOT 403, AND THAT NEARLY COST US ELEVEN LINKS.
# Verified 2026-08-17: `https://github.com/haabe/mycelium/commit/96b485e` returns 404 to
# curl while `gh api repos/haabe/mycelium/commits/96b485e` returns the full SHA — the
# commit plainly exists. Same for `/issues`, which 404s while the API reports
# has_issues: true. Every other site in this corpus signals bot-refusal with 401/403,
# which the classifier already handles; GitHub uses the one code that means "gone".
# Without this, seven receipt commit links, a privacy-policy issues link and three
# upstream issue links were two runs from being declared ROTTED.
GITHUB_HTML = re.compile(r"^https?://(www\.)?github\.com/(?P<rest>.+)$", re.IGNORECASE)


def github_api_confirms(url: str, timeout: int) -> bool | None:
    """True if the GitHub API says this path exists, False if not, None if unusable."""
    m = GITHUB_HTML.match(url)
    if not m:
        return None
    parts = m.group("rest").split("#")[0].split("?")[0].strip("/").split("/")
    if len(parts) < MIN_REPO_PATH_PARTS:
        return None
    owner, repo, rest = parts[0], parts[1], parts[2:]
    if not rest:
        api = f"https://api.github.com/repos/{owner}/{repo}"
    elif rest[0] == "commit" and len(rest) > 1:
        api = f"https://api.github.com/repos/{owner}/{repo}/commits/{rest[1]}"
    elif rest[0] == "issues" and len(rest) > 1 and rest[1].isdigit():
        api = f"https://api.github.com/repos/{owner}/{repo}/issues/{rest[1]}"
    elif rest[0] in ("issues", "discussions", "pulls", "tree", "blob"):
        api = f"https://api.github.com/repos/{owner}/{repo}"   # repo-level existence
    else:
        return None
    req = _request(api, {"User-Agent": UA, "Accept": "application/vnd.github+json"})
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with _urlopen(req, timeout):
            return True
    except urllib.error.HTTPError as e:
        return False if e.code == HTTP_NOT_FOUND else None
    except Exception:  # noqa: BLE001
        return None


def _classify_http_error(e: urllib.error.HTTPError, url: str, timeout: int) -> tuple[str, str]:
    """Turn an HTTP status into one of this file's four verdicts.

    Extracted from `probe` 2026-08-26. It holds all three design rules from the
    module docstring, and every branch traces to a specific 2026-08-17 finding —
    which is exactly why it is worth reading on its own rather than as the tail of
    a try block.
    """
    if e.code in HTTP_GONE:
        confirmed = github_api_confirms(url, timeout)
        if confirmed is True:
            return OK, f"{e.code} to robots, but the GitHub API confirms it exists"
        if confirmed is None and GITHUB_HTML.match(url):
            return UNKNOWN, f"{e.code} and the GitHub API could not settle it"
        return PENDING, f"{e.code}"
    if e.code in HTTP_BOT_WALL:
        # Rule 2: a bot wall is not a dead page.
        return BLOCKED, f"{e.code} (bot wall — a human can open this)"
    # Rule 1: 429 and 5xx mean WE could not look.
    return UNKNOWN, f"{e.code} (could not check)"


def probe(url: str, timeout: int) -> tuple[str, str]:
    """Return (status, detail). Never returns ROTTED — escalation needs history."""
    req = _request(url, {"User-Agent": UA})
    try:
        with _urlopen(req, timeout) as r:
            return OK, f"{r.status}"
    except urllib.error.HTTPError as e:
        return _classify_http_error(e, url, timeout)
    except Exception as e:  # noqa: BLE001 — DNS, TLS, timeout, redirect loops
        return UNKNOWN, f"{type(e).__name__} (could not check)"


def newest_snapshot(before: datetime.date | None = None) -> tuple[datetime.date | None, dict]:
    """Newest snapshot STRICTLY OLDER than `before`.

    The `before` guard is not cosmetic. Snapshots are keyed by date, so a second
    run on the same day would otherwise read TODAY'S OWN snapshot as "the previous
    run" and escalate every pending link to ROTTED on the spot. Two --force runs
    minutes apart manufactured three rotted citations that way on 2026-08-17,
    which is a fabricated finding of exactly the kind this check exists to prevent.
    A strike has to be a separate DAY, not a separate invocation.
    """
    sd = snap_dir()
    if not sd.is_dir():
        return None, {}
    for snap in sorted(sd.glob("*.json"), reverse=True):
        try:
            when = datetime.date.fromisoformat(snap.stem)
        except ValueError:
            continue  # browser-verified.json and friends
        if before is not None and when >= before:
            continue
        try:
            return when, json.loads(snap.read_text())
        except (ValueError, OSError) as e:
            # Skipping silently would let a corrupt newest snapshot hand the strike history to
            # an older one, and a link could rot or clear on a day it was never probed.
            print(f"  WARNING: snapshot {snap.name} is unreadable ({type(e).__name__}); using "
                  f"the next older one for strike history. Fix or delete the file.",
                  file=sys.stderr)
            continue
    return None, {}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    ap.add_argument("--today", default=None, help="override for testing (YYYY-MM-DD)")
    ap.add_argument("--max-age-days", type=int, default=14,
                    help="no-op if the newest snapshot is younger than this")
    ap.add_argument("--force", action="store_true", help="run even if a recent snapshot exists")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--strict", action="store_true", help="exit 1 when a link is ROTTED")
    ap.add_argument("--limit", type=int, default=0, help="probe only the first N urls (testing)")
    ap.add_argument("--mark-verified", metavar="URL",
                    help="record a browser verdict for a bot-walled URL, then exit")
    ap.add_argument("--verdict", choices=("ok", "gone", "unclear"), default="ok",
                    help="with --mark-verified: what the browser actually showed. `unclear` is a "
                         "first-class answer — see below")
    ap.add_argument("--note", default="", help="with --mark-verified: what you saw")
    ap.add_argument("--include-framework", action="store_true",
                    help="ALSO scan the framework's own docs. Roadmap-only: a consumer must "
                         "never do this — see FRAMEWORK_GLOBS comment")
    ap.add_argument("--framework-root", default=None,
                    help="path to the framework repo; defaults to state/upstream.json")
    ap.add_argument("--browser-verify-days", type=int, default=90,
                    help="how long a browser verdict stands before it is asked for again")
    return ap


def resolve_framework_root(args: argparse.Namespace) -> pathlib.Path | None:
    """The framework tree to ALSO scan, or None with a printed reason.

    Returning None silently would be the absence-laundered-into-a-default shape
    this check exists to catch, so the miss is always announced.
    """
    cand = [pathlib.Path(args.framework_root)] if args.framework_root else []
    try:
        state = (ROOT / ".claude/state/upstream.json").read_text()
        repo = json.loads(state).get("upstream_repo")
    except (OSError, ValueError):
        repo = None
    if repo:
        cand.append(pathlib.Path(repo))
    fw = next((c for c in cand if (c / "plugins" / "mycelium").is_dir()), None)
    if fw is None:
        print("  --include-framework asked for but no framework tree found; "
              "scanning project surfaces only")
    return fw


def _verdict_is_fresh(v: dict, today: datetime.date, max_age_days: int) -> bool:
    try:
        return (today - datetime.date.fromisoformat(v["checked_at"])).days <= max_age_days
    except (ValueError, KeyError):
        return False


def apply_browser_verdict(rec: dict, v: dict) -> None:
    """A HUMAN WHO OPENED THE PAGE OUTRANKS THE PROBE, WHATEVER THE PROBE SAID.

    Originally gated on `status == BLOCKED`, and that was wrong: the three URLs
    verified by hand on 2026-08-17 came back PENDING (404), not BLOCKED, so their
    verdicts were recorded and then silently ignored.

    All three verdicts are asymmetric on purpose:
      ok      -> OK immediately. Without this a URL a human SAW alive keeps its
                 PENDING 404 and rots on the next run — the fabricated finding this
                 check exists to prevent, arriving through the door built to stop it.
      gone    -> ROTTED with no second strike. A browser reporting absence is
                 evidence, not the guess a urllib 404 is.
      unclear -> UNKNOWN. Added 2026-08-17 because the tool could not say what had
                 happened: a LinkedIn URL returned a generic "Something went wrong"
                 in a logged-in browser, which is consistent with deletion AND with
                 a platform error, and the platform never says which. Forcing that
                 into ok or gone would have invented an answer. The attempt is
                 logged so the nudge stops asking; the status stays UNKNOWN so
                 nothing downstream reads it as alive or as rotted.
    """
    when = v["checked_at"]
    rec["browser_verdict"] = v["verdict"]
    rec["browser_checked_at"] = when
    rec["needs_browser_check"] = False
    if v["verdict"] == "ok":
        rec["status"], rec["detail"] = OK, f"seen alive in a browser on {when}"
    elif v["verdict"] == "gone":
        rec["status"], rec["detail"] = ROTTED, f"confirmed gone in a browser on {when}"
    elif v["verdict"] == "unclear":
        rec["status"] = UNKNOWN
        rec["detail"] = (f"looked in a browser on {when} and still could not tell — "
                         f"platform returned a generic error")


def classify(urls: list[str], cited: dict[str, list[str]], prev_status: dict[str, str],
             args: argparse.Namespace, today: datetime.date) -> dict[str, dict]:
    """Probe every url and settle its status. No printing, no disk."""
    verified = load_verified()
    results: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        probed = ex.map(lambda u: probe(u, args.timeout), urls)
        for url, (raw_status, detail) in zip(urls, probed, strict=True):
            # Rule 3: escalate to ROTTED only on a second consecutive failure.
            status = (ROTTED if raw_status == PENDING
                      and prev_status.get(url) in (PENDING, ROTTED) else raw_status)
            rec = {"status": status, "detail": detail, "cited_by": cited[url]}

            v = verified.get(url)
            fresh = bool(v) and _verdict_is_fresh(v, today, args.browser_verify_days)
            if fresh:
                apply_browser_verdict(rec, v)
            elif status == BLOCKED:
                rec["needs_browser_check"] = True
            results[url] = rec
    return results


def _report_rotted(rotted: dict) -> None:
    print("\nROTTED — failed on two consecutive runs. The claim citing these can no longer be\n"
          "checked by anyone. Before deleting: the four found on 2026-08-17 had all MOVED, and\n"
          "two had been recorded under the wrong title. Search for the title before the URL.")
    for u, v in rotted.items():
        print(f"  {v['detail']:<10} {u}\n{'':<13}cited by {', '.join(v['cited_by'])}")


def _report_pending(pending: dict) -> None:
    print(f"\npending — first failing run for {len(pending)}. NOT reported as rot yet; a single\n"
          "404 can be a deploy blip. Confirmed or cleared on the next run.")
    for u, v in list(pending.items())[:PENDING_SHOWN]:
        print(f"  {v['detail']:<10} {u}")


def _report_blocked(blocked: dict) -> None:
    want = {u: v for u, v in blocked.items() if v.get("needs_browser_check")}
    done = len(blocked) - len(want)
    print(f"\nblocked — {len(blocked)} refused a robot (401/403). NOT rot: a human can open these."
          + (f" {done} already carry a browser verdict." if done else ""))
    if not want:
        return
    print("\n  ASK: these need a look in the browser, because urllib cannot settle them and\n"
          "  guessing either way would be a fabricated finding. Open each with the\n"
          "  claude-in-chrome MCP (the session is logged in where these walls are not),\n"
          "  confirm the page is still there, then record the verdict so this stops asking:")
    for u, v in want.items():
        print(f"    {u}\n      cited by {', '.join(v['cited_by'])}")
    first = next(iter(want))
    print(f'\n  python3 {sys.argv[0]} --mark-verified "{first}" --verdict ok --note "what you saw"')
    print("  (--verdict gone marks it ROTTED immediately — a browser saying the page is\n"
          "   absent is evidence, not a guess, so it does not wait for a second strike.)")


def report(urls: list[str], cited: dict[str, list[str]], results: dict[str, dict]) -> dict:
    """Print the human report. Returns the buckets so the caller need not re-derive them."""
    by = collections.Counter(v["status"] for v in results.values())
    buckets = {name: {u: v for u, v in results.items() if v["status"] == name}
               for name in (ROTTED, PENDING, UNKNOWN, BLOCKED)}
    files = {f for fs in cited.values() for f in fs}

    print(f"  {len(urls)} cited urls across {len(files)} files")
    print(f"  {by[OK]} ok · {len(buckets[ROTTED])} ROTTED · {len(buckets[PENDING])} pending · "
          f"{len(buckets[BLOCKED])} blocked · {len(buckets[UNKNOWN])} unknown")

    if buckets[ROTTED]:
        _report_rotted(buckets[ROTTED])
    if buckets[PENDING]:
        _report_pending(buckets[PENDING])
    if buckets[BLOCKED]:
        _report_blocked(buckets[BLOCKED])
    if buckets[UNKNOWN]:
        print(f"\nunknown — {len(buckets[UNKNOWN])} could not be checked "
              f"(429, 5xx, timeout, DNS/TLS).\n"
              "Not a finding in either direction. If this number is large the run was throttled,\n"
              "not the evidence base rotting.")

    print(f"\n{by[OK]} ok, {len(buckets[ROTTED])} rotted, {len(buckets[PENDING])} pending, "
          f"{len(buckets[BLOCKED])} blocked, {len(buckets[UNKNOWN])} unknown")
    return buckets


def main(argv: list[str] | None = None) -> int:
    global ROOT  # noqa: PLW0603 — one root per run, set before any path is touched
    args = build_parser().parse_args(argv)
    ROOT = pathlib.Path(args.project_dir)
    if not (ROOT / ".claude").is_dir():
        print(f"evidence-links: NOT A PASS — no .claude/ under {ROOT}. Nothing was checked.")
        return 2

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.datetime.now().astimezone().date())

    if args.mark_verified:
        mark_verified(args.mark_verified, args.verdict, args.note, today)
        print(f"recorded: {args.verdict} for {args.mark_verified} (browser, {today})")
        return 0

    # TWO LOOKUPS, BECAUSE THE THROTTLE AND THE STRIKE HISTORY WANT OPPOSITE THINGS.
    # Regression introduced 2026-08-17 and caught 2026-08-18 by a snapshot that would
    # not stay committed: the `before=today` guard (added so a same-day re-run cannot
    # count as a second strike) was ALSO feeding the throttle, so on any same-day re-run
    # prev_date was None, the cadence check never fired, and every push did ~390 network
    # requests. The throttle asks "when did this last run at all", which must include
    # today. The strike history asks "did this fail on a PREVIOUS DAY", which must not.
    throttle_date, _ = newest_snapshot()
    _prev_date, prev = newest_snapshot(before=today)

    print("Evidence link check")
    print("=" * 60)

    if throttle_date and not args.force:
        age = (today - throttle_date).days
        if age < args.max_age_days:
            print(f"  skipped — last run {age}d ago, cadence is {args.max_age_days}d. "
                  f"--force to run anyway.")
            return 0

    fw = resolve_framework_root(args) if args.include_framework else None

    cited = collect(framework_root=fw)
    urls = sorted(cited)
    if args.limit:
        urls = urls[:args.limit]
    if not urls:
        print("  no urls found under any SEARCH_ROOT — check the paths exist")
        return 0

    prev_status = {u: v.get("status") for u, v in (prev.get("urls") or {}).items()}
    results = classify(urls, cited, prev_status, args, today)

    snap_dir().mkdir(parents=True, exist_ok=True)
    counts = dict(collections.Counter(v["status"] for v in results.values()))
    (snap_dir() / f"{today}.json").write_text(json.dumps(
        {"checked_at": str(today), "counts": counts, "urls": results}, indent=1))

    buckets = report(urls, cited, results)
    return 1 if (args.strict and buckets[ROTTED]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
