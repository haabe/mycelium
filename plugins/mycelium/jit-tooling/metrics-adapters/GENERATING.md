# Generating a New Metrics Adapter

Mycelium does NOT pre-ship a catalog of adapters. The detector identifies which metric sources apply to the user's project, and the agent generates an adapter the first time a novel source is encountered. This is the same philosophy as `jit-tooling/detector.md` — Mycelium does not ship test runners; it detects which one the user has and configures it. Metrics work the same way.

**Your goal as the generating agent:** produce a new `metrics-adapters/<source>.md` that a future agent (possibly a different session, possibly you after compaction) can follow to pull data from the source without any handover from the user.

## When to generate

- `/metrics-detect` identifies a source (e.g., Plausible env var, Stripe SDK) that has no adapter file in `metrics-adapters/`.
- The user adds a source to `active-metrics.yml` manually and asks to run `/metrics-pull`, and the adapter is missing.
- An existing adapter's `last_known_working` is more than 180 days old AND a run fails — regenerate rather than patch.

## Inputs you have

Before writing the adapter, collect:

1. **The template**: `metrics-adapters/TEMPLATE.md` — the required shape.
2. **The reference adapter**: `metrics-adapters/github.md` — a fully-worked traffic-class example.
3. **Vendor documentation**: use `mcp__context7` for library/API docs, `WebFetch` for vendor API reference pages.
4. **The user's confirmation** on credential approach — ask what auth they have set up. Do NOT assume.

## Generation workflow

### Step 1 — Classify the source

Pick ONE `source_class`:

| Class | When to pick |
|-------|--------------|
| `traffic` | Views, sessions, referrers, pageviews (GitHub, Plausible, GA, Fathom, PostHog pageviews) |
| `events` | Discrete business events — subscriptions, errors, webhooks, transactions (Stripe, Segment, Sentry) |
| `reviews` | User-submitted ratings/reviews (App Store Connect, Play Console, Trustpilot) |
| `support` | Support tickets, issues, conversations (Intercom, Zendesk, Linear, GitHub Issues) |

If a source straddles two classes (e.g., PostHog does both pageviews AND events), write TWO adapters — `posthog_traffic.md` and `posthog_events.md` — rather than one hybrid adapter. One source_class per adapter file.

### Step 2 — Map the source's native data onto the schema

Work through the template section by section:

1. **primary_counts** — the source's headline numbers. Keep it short; 3-6 fields.
2. **traffic / referrers / top_paths** — include ONLY if `source_class: traffic`. For `reviews`/`support`, consider repurposing (see below). For `events`, omit.
3. **custom_signals** — everything else that's useful but doesn't fit. At least one **ratio** that pressures against vanity metrics (Goodhart).

### Step 3 — Handle the "doesn't fit" cases honestly

**The temptation trap** (observed in all three 2026-04-16 assumption tests): faced with a required-looking field that doesn't match, the agent wants to invent a mapping.

Reject these temptations:
- Mapping payment methods onto `referrers` because both are strings.
- Inventing a fake `traffic.views` by calling review impressions "views".
- Using `reviewerNickname` as a referrer name.

The honest options are:
1. **Omit** the field (for non-traffic classes, just don't include `traffic`/`referrers`/`top_paths`).
2. **Repurpose** under documented interpretation (allowed for `reviews` and `support` only). You MUST declare the reinterpretation in `custom_signals.field_interpretations`.
3. **Use `custom_signals`** as the escape valve.

If you catch yourself inventing a mapping, stop and omit instead.

### Step 4 — Write the adapter

Copy `TEMPLATE.md` to `metrics-adapters/<source>.md`. Fill in every section. Use `github.md` as the shape reference — length and detail should be similar. Don't skip "Failure modes" or "Freshness" — those are where future-you will thank present-you.

### Step 5 — Validate before presenting

Before saving, verify:

- [ ] Every command listed in "Pull" runs without interactive prompts (given the stated credentials).
- [ ] Schema fields match the class rules (no empty-array `referrers` on an `events` adapter).
- [ ] `custom_signals` includes at least one ratio that isn't gameable by simple volume inflation.
- [ ] Canvas routing names real canvas files (check `canvas/*.yml`).
- [ ] `last_known_working` is set to today.

### Step 6 — Present to user

Show the drafted adapter to the user. Ask:

1. "I drafted an adapter for `<source>` based on [docs/CLI/env-var you found]. Should I save it as `metrics-adapters/<source>.md`?"
2. "Credentials needed: `<credential_requirement>`. Do you have that set up, or do I need to guide you through it?"

Wait for confirmation before writing and before adding the source to `active-metrics.yml`.

### Step 7 — Save and register

Write the adapter to `metrics-adapters/<source>.md`. Add or update the entry in `active-metrics.yml`:

```yaml
sources:
  <source>:
    target: "..."
    adapter_generated_at: "YYYY-MM-DD"
    adapter_version: 1
```

## Quality bar

A generated adapter is good enough if a future agent in a fresh session, with only the adapter file and the credentials, can run `/metrics-pull` and produce a valid snapshot.

The three assumption tests that validated this workflow (2026-04-16) showed subagents CAN do this from just the template + GitHub example + vendor docs. If you are that agent and you're feeling stuck, the likely root cause is that your `source_class` choice is wrong, OR you are fighting a repurposing that should be an omission instead.

## Anti-patterns to avoid

| Smell | Fix |
|-------|-----|
| Empty arrays on non-traffic classes | Omit the whole field. |
| Every number mapped onto the schema | Use `custom_signals` for the overflow. |
| No ratio in `custom_signals` | Find one — Goodhart gate. |
| Raw vendor field names preserved | Normalize. Downstream readers shouldn't need vendor docs. |
| Credentials embedded in adapter | Never. Always reference env vars / CLI auth. |
| "TODO: handle rate limit" | Delete the TODO or implement it now. An adapter with TODOs is not ready to ship. |

## If you can't generate an adapter

If the source has no public API, no CLI, or requires interactive OAuth with no programmatic path:

1. Document the gap in the adapter file anyway, with `adapter_version: 0` and a clear `failure_modes` section.
2. Flag to the user: "This source requires manual export. Consider setting up a scheduled export that writes to disk, and I can adapt to read the export instead."
3. Do NOT pretend to generate a working adapter. Partial success is worse than honest failure.
