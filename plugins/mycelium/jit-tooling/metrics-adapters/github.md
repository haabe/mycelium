# GitHub Metrics Adapter

Reference adapter. Pulls repository engagement and traffic data from GitHub for any `github.com/<owner>/<repo>` target declared in `active-metrics.yml`.

This adapter is both the production adapter Mycelium ships with AND the worked example that `GENERATING.md` points at when the agent has to generate a new adapter for a novel source. Study its shape before writing a new one.

## Identity

- **source**: `github`
- **source_class**: `traffic`
- **credential_requirement**: `gh` CLI authenticated with write scope on the target repo (the traffic endpoints require push access).
- **last_known_working**: `2026-04-16`
- **adapter_version**: `1`

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

## Pull

Run these `gh api` calls in parallel. `$TARGET` is `active-metrics.yml :: sources.github.target`.

```
gh api repos/$TARGET --jq '{stars: .stargazers_count, forks: .forks_count, watchers: .subscribers_count, open_issues: .open_issues_count}'
gh api repos/$TARGET/traffic/views
gh api repos/$TARGET/traffic/clones
gh api repos/$TARGET/traffic/popular/referrers
gh api repos/$TARGET/traffic/popular/paths
```

Notes:
- Traffic endpoints return the last 14 days only.
- Data updates hourly.
- Referrers and paths are top-10 only.
- If any endpoint returns empty in the first hour after a window reset, emit `fetch_status: partial` in the snapshot rather than zeroing out.

## Normalize

Emit a snapshot matching the shared schema (`metrics-adapters/TEMPLATE.md`):

```yaml
source: "github"
source_class: "traffic"
target: "owner/repo"
fetched_at: "YYYY-MM-DDTHH:MM:SSZ"
adapter_version: 1

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
