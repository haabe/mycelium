# GitHub Metrics Adapter

Reference adapter. Pulls repository engagement and traffic data from GitHub for any `github.com/<owner>/<repo>` target declared in `active-metrics.yml`.

This adapter is both the production adapter Mycelium ships with AND the worked example that `GENERATING.md` points at when the agent has to generate a new adapter for a novel source. Study its shape before writing a new one.

## Identity

- **source**: `github`
- **source_class**: `traffic`
- **credential_requirement**: `gh` CLI authenticated with write scope on the target repo (the traffic endpoints require push access).
- **last_known_working**: `2026-08-05`
- **adapter_version**: `2`  # v2 adds optional landscape comparators; v1 snapshots stay readable (the block is simply absent)

## Target

Read the `target` for this adapter from `active-metrics.yml`:

```yaml
sources:
  github:
    target: "owner/repo"        # required
    window_days: 14             # optional, defaults to 14 (GitHub traffic API max)
    known_referrers: [...]      # optional override of the defaults below
```

If `target` is missing, abort and ask the user which repo to track. Do not silently fall back.

### Comparators (optional, adapter_version 2+)

```yaml
sources:
  github:
    target: "owner/repo"
    comparators:                       # optional; 0-5 public repos
      - repo: "other/repo"
        why: "same play, narrower scope"   # required — see below
        canvas_ref: "landscape.yml#comp-073"  # optional
```

**Why this exists.** Your own counts tell you whether a number moved; they cannot tell you
whether it moved *for you specifically* or for everyone doing this kind of thing. A same-play
repo pulled on the SAME DAY is the closest thing a solo project gets to a control: it shares
the platform, the season, and the discovery channels, so a divergence between the two is
about the products rather than the weather. Dogfood instance — a project read its own flat
fork count as market indifference for weeks; a competitor found later had more than twice the
forks on fewer stars from a repo created ten days after it, which reframes the same number
from "nobody forks tools like this" to "people fork tools like this, not this one."

**`why` is REQUIRED and is not decoration.** A comparator without a stated basis of
comparison is a leaderboard, and a leaderboard is a Goodhart engine pointed at a number you
do not control. Writing down what makes the repo comparable is also what makes it
falsifiable: when the `why` stops being true (they pivot, they add a team, they get
acquired), the comparison stops meaning anything and the entry should be dropped rather than
silently kept.

**PRIVACY — comparators are held to a STRICTER rule than `target`, deliberately.**
Persist repo-level COUNTS ONLY: `stars`, `forks`, `watchers`, `open_issues`, `created_at`.
Do NOT fetch or persist stargazer dates, contributor lists, or traffic for a comparator.
Traffic endpoints require push access and will fail anyway, but the binding reason is not
the API: **you have no relationship with these people.** For your own repo, per-date
stargazer buckets are defensible telemetry about your own project. For someone else's,
building a longitudinal record of who-starred-when is surveillance of a third party's users,
and it stays out of the snapshot whether or not an endpoint would serve it.

**Failure is non-fatal and must be visible.** If a comparator 404s (deleted, renamed, made
private), record `fetch_status: "unavailable"` with the reason for that entry and continue.
A vanished competitor is itself a signal and must not be silently dropped — an entry that
disappears from the snapshot reads as "never tracked", which is the absent-vs-negative
confusion this framework removes elsewhere.

## Pull

Run these `gh api` calls in parallel. `$TARGET` is `active-metrics.yml :: sources.github.target`.

```
gh api repos/$TARGET --jq '{stars: .stargazers_count, forks: .forks_count, watchers: .subscribers_count, open_issues: .open_issues_count}'
gh api repos/$TARGET/traffic/views
gh api repos/$TARGET/traffic/clones
gh api repos/$TARGET/traffic/popular/referrers
gh api repos/$TARGET/traffic/popular/paths
```

**Star landing DATES (optional, for star attribution).** The five calls above give star *counts* but never *when* a star landed, so a count delta can only ever be `consistency_only` on cause. To capture per-date landings — which lets a pull check whether new stars fell inside a known event window (a post/launch date) — pull `starred_at` timestamps:

```
gh api repos/$TARGET/stargazers --paginate -H "Accept: application/vnd.github.star+json" --jq '.[].starred_at'
```

- **Privacy (HARD RULE): bucket to dates, never persist usernames.** The `star+json` payload includes `user.login` — do NOT write it to the snapshot. Reduce the stream to per-date counts before emitting (`.[].starred_at` already drops the login above). Stargazer identity is third-party PII; committed snapshots stay identity-free per privacy-by-design. Username lookups are an ad-hoc live operation only, never committed.
- **Cost guard.** Stargazers paginate oldest-first; reaching recent stars on a large repo costs `ceil(stars/100)` calls. Pull this only when `primary_counts.stars <= 1000`; above that, skip it and note `stargazer_dates: skipped (cost guard, stars > 1000)` in the snapshot.
- Emit only the dates inside the snapshot window (`window_days`); older landings are not attribution-relevant and stay uncounted.

**Comparator pull (adapter_version 2+).** One call per configured comparator, run in the same
batch as the calls above so both repos are read at the same moment — a comparison assembled
from two different days measures the gap between the days as much as the repos:

```
gh api repos/$COMPARATOR --jq '{stars: .stargazers_count, forks: .forks_count, watchers: .subscribers_count, open_issues: .open_issues_count, created_at: .created_at}'
```

- **That is the ONLY call permitted per comparator.** No traffic, no stargazers, no
  contributors — see the privacy rule under Target. The restriction is deliberate and is not
  a consequence of the API: comparator repos belong to people you have no relationship with.
- **`--jq` is not a formality.** Fetching the full repo object and selecting fields afterwards
  pulls owner blocks and profile data into the process; project the fields at the API boundary
  so third-party detail is never in hand to leak into a snapshot by accident.
- On non-zero exit or 404, emit that comparator with `fetch_status: "unavailable"` and the
  reason, and continue with the rest of the pull.
- **Never let comparators fail the pull.** Your own metrics are the point; a competitor's
  counts are context.

Notes:
- Traffic endpoints return the last 14 days only.
- Data updates hourly.
- Referrers and paths are top-10 only.
- If any endpoint returns empty in the first hour after a window reset, emit `fetch_status: partial` in the snapshot rather than zeroing out.

## Normalize

Emit a snapshot matching the shared schema (`${CLAUDE_PLUGIN_ROOT}/jit-tooling/metrics-adapters/TEMPLATE.md`):

```yaml
source: "github"
source_class: "traffic"
target: "owner/repo"
fetched_at: "YYYY-MM-DDTHH:MM:SSZ"
adapter_version: 2

# Landscape comparators (adapter_version 2+). ABSENT when none configured — an empty list
# and a missing key mean different things and both are honest; what is NOT allowed is
# omitting a comparator that was configured but failed to fetch (see fetch_status below).
comparators:
  - repo: "other/repo"
    why: "same play, narrower scope"        # copied from config; the basis of comparison
    canvas_ref: "landscape.yml#comp-073"    # optional
    fetch_status: "ok"                      # ok | unavailable
    counts:                                 # COUNTS ONLY — no stargazer dates, no contributors,
      stars: <int>                          # no traffic. See the privacy rule in Target above.
      forks: <int>
      watchers: <int>
      open_issues: <int>
      created_at: "YYYY-MM-DDTHH:MM:SSZ"    # lets a reader weigh age against counts

primary_counts:
  stars: <int>
  forks: <int>
  watchers: <int>
  open_issues: <int>

traffic:
  window_days: 14
  views:
    total: <int>
    unique: <int>
  clones:
    total: <int>
    unique: <int>

referrers:
  - { name: "<referrer>", count: <int>, unique: <int>, known: <bool> }

top_paths:
  - { path: "<path>", count: <int>, unique: <int> }

stargazer_dates:                  # OPTIONAL (added plugin v0.41.6); omit if not pulled or cost-guarded
  in_window:                      # date-only; usernames NEVER persisted (privacy-by-design)
    "YYYY-MM-DD": <int>           # count of stars that landed that day, within window_days
  window_total: <int>            # stars landed inside the window

custom_signals:
  clone_to_star_ratio: <float>    # clones.total / max(primary_counts.stars, 1)
  view_to_clone_ratio: <float>    # views.total / max(clones.total, 1)
```

## Known referrers (default "not surprising")

These referrers are the baseline for the Mycelium project itself. For other targets, override via `active-metrics.yml :: sources.github.known_referrers`.

- `github.com` — internal navigation / fork traffic
- `Google` — organic discovery
- `duckduckgo.com`, `bing.com` — organic discovery
- `linkedin.com`, `lnkd.in` — LinkedIn posts
- `reddit.com`, `com.reddit.frontpage`, `old.reddit.com` — Reddit
- `news.ycombinator.com` — Hacker News
- `facebook.com`, `l.facebook.com`, `lm.facebook.com`, `m.facebook.com` — Facebook
- `twitter.com`, `t.co`, `x.com` — X/Twitter

Any referrer NOT in the known list with `unique >= 5` is flagged as unexplained in the snapshot's `custom_signals.unexplained_referrers` list.

## Delta rules

When computing deltas against the prior snapshot:
- **primary_counts**: current minus prior, plus days-since-prior.
- **traffic.views / traffic.clones**: highlight the newest day not present in the prior snapshot. Window-to-window totals are approximate because the 14-day window overlaps.
- **referrers / top_paths**: report new entries, dropped entries, and rank shifts ≥3 positions.
- **comparators** (if configured): report each comparator's own delta, then the RATIO OF
  DELTAS against `target` over the same interval — that ratio is the entire point, because
  both repos were pulled the same day through the same platform. **Report the ratio and
  refuse to rank.** State it as "target +N, comparator +M over D days" plus the standing
  totals; do NOT emit a winner, a position, or a percentage gap. At the counts a young
  project actually has (single digits either way), a ratio is a hypothesis and a rank is a
  fiction. **Flag a DIVERGENCE only when the two move in opposite directions across two
  consecutive pulls** — one pull is noise, and same-direction movement at different speeds is
  usually the platform, not the products.
- **stargazer_dates** (if captured): report the date(s) new stars landed on since the prior snapshot, and flag any landing inside an active event window (a post/launch/outreach date from a human-task or canvas event). A star whose date aligns with a known event is stronger than a bare count delta — but date-alignment alone stays `consistency_only` (a date is not a source; concurrent referrers remain equally plausible). The signal it DOES settle cleanly: whether N new stars fell in-window at all, which a count delta across overlapping pulls cannot.

## Canvas routing

GitHub metrics feed three canvas files. `/metrics-pull` drafts evidence entries for whichever apply given the current diamond.

- `purpose.yml` — general traction (stars, forks, clone-to-star ratio). Evidence entry uses `type: market_signal`, `source_class: external_data`.
- `north-star.yml` — if the project's north-star metric is repo-engagement-based (open source projects often are), emit a time-series data point.
- `go-to-market.yml` — on launch weeks, the 14-day view/clone totals and referrer mix are launch evidence.

## Investigation hooks (for unexplained referrers)

Before reporting an unexplained referrer to the user, attempt a quick investigation:

```
curl -s "https://hn.algolia.com/api/v1/search?query=$(printf '%s' "$TARGET" | sed 's|/|%2F|g')&restrictSearchableAttributes=url"
```

Add findings to `custom_signals.referrer_notes` in the snapshot.

## Failure modes

| Failure | Behavior |
|---------|----------|
| `gh` not authenticated | Report to user: "Run `gh auth login` with scope including repo traffic." Abort. |
| `gh` authenticated but lacks push scope on target | Primary counts will succeed; traffic endpoints return 403. Emit `fetch_status: partial`, skip `traffic`/`referrers`/`top_paths`. |
| Target repo does not exist or is private to the agent | Abort with clear error. |
| Rate limited | Report the reset time from `gh api rate_limit` and retry once after 60s. Do not retry more than once per invocation. |

## Theory grounding

- Goodhart: pair stars (gameable) with clone-to-star ratio (harder to fake — requires an actor to actually clone).
- Gilad: replace "I checked GitHub" memory with timestamped, diffable snapshots.
- Torres: evidence-based progression. The snapshot is the evidence; the report is the summary.
