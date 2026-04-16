# Metrics Adapter Template

An adapter teaches the agent how to pull, normalize, and interpret data from one external metrics source. Adapters are **instructions, not code** — consistent with how the rest of Mycelium works. The agent reads the adapter and executes the steps.

Copy this file to `metrics-adapters/<source>.md` and fill in every section. Delete this preamble and the "EDIT ME" hints when you're done.

## Identity

- **source**: `<short identifier, lowercase, snake_case>` (e.g., `github`, `plausible`, `app_store_connect`)
- **source_class**: `traffic | events | reviews | support` — pick ONE. See `metrics-detector.md :: Source classes` if unsure.
- **credential_requirement**: what the user must have set up (env var, CLI auth, API key path). Mycelium does NOT store secrets.
- **last_known_working**: `YYYY-MM-DD` — date this adapter was last verified against the live API.
- **adapter_version**: `1` — increment when the adapter changes its output shape or pull logic.

## Target

Declare what configuration the adapter reads from `active-metrics.yml`. At minimum a `target` (the specific instance being tracked). Example:

```yaml
sources:
  <source>:
    target: "<identifier>"     # required — e.g., site domain, product id, app id
    window_days: <int>          # optional, source-appropriate default
    # ...any other source-specific config
```

If a required field is missing, the adapter MUST abort with a clear error rather than silently fall back.

## Pull

List the exact commands or HTTP calls the agent will make. Prefer vendor CLIs over raw HTTP where they exist (they handle auth). Use `$TARGET` and similar placeholders.

Document:
- Rate limits and windowing behavior
- Update cadence (hourly? daily? real-time?)
- Any endpoint quirks (truncation, pagination, data delay)

## Normalize

Emit a snapshot matching the shared schema below. **Fields that do not apply to this source class MUST be omitted entirely** — not emitted as empty arrays or null. Empty implies "we looked and found nothing"; omission implies "this concept doesn't apply here."

### Required for ALL classes

```yaml
source: "<source>"
source_class: "<traffic | events | reviews | support>"
target: "<target identifier>"
fetched_at: "YYYY-MM-DDTHH:MM:SSZ"
adapter_version: <int>

primary_counts:
  <source-specific headline counts>
```

### Required for class `traffic`, omit for others (or repurpose — see below)

```yaml
traffic:
  window_days: <int>
  views:   { total: <int>, unique: <int> }
  clones:  { total: <int>, unique: <int> }  # optional even within traffic class

referrers:
  - { name: "<ref>", count: <int>, unique: <int>, known: <bool> }

top_paths:
  - { path: "<path>", count: <int>, unique: <int> }
```

### Universal escape valve

```yaml
custom_signals:
  <key>: <value>
  # Anything that doesn't fit: ratios, mixes, freshness indicators, regulatory flags.
  # If this adapter flags unexplained signals, put the list here:
  # unexplained_referrers: [...]
```

### Field repurposing (reviews / support classes)

`reviews` and `support` adapters MAY reuse `referrers` or `top_paths` under a new interpretation — e.g., `top_paths` as top-reviewed items, `referrers` as review territories. If you do this, you MUST declare the reinterpretation in `custom_signals.field_interpretations` so downstream readers are not misled:

```yaml
custom_signals:
  field_interpretations:
    top_paths: "top-reviewed products by volume"
    referrers: "reviews grouped by storefront territory"
```

Do not repurpose for `traffic` or `events` adapters — if the field doesn't apply, omit it.

### Do NOT

- Do NOT invent data to fill required-looking fields. If the source doesn't have it, omit it (or, for non-applicable classes, repurpose with documented interpretation).
- Do NOT map source concepts onto schema fields when the semantics don't match (e.g., mapping payment methods onto `referrers` because both are strings). The Stripe and App Store assumption tests (2026-04-16) explicitly rejected these temptations.

## Delta rules

Explain how this adapter's data should be compared across snapshots:
- Which fields are cumulative (e.g., stars) vs windowed (e.g., 14-day views)
- How overlapping windows affect interpretation
- Which field changes are "interesting" (warrant flagging to the user)

## Canvas routing

Which canvas files does this source feed? List each target file + the evidence type + when the routing applies. Example:

- `purpose.yml` — `type: market_signal`, `source_class: external_data`. General traction.
- `north-star.yml` — when the project's north star is tied to this source's headline metric.
- `go-to-market.yml` — on launch/campaign weeks.

`/metrics-pull` uses this to draft evidence entries.

## Failure modes

| Failure | Behavior |
|---------|----------|
| Credential missing | Clear error, point to credential_requirement. Abort. |
| Credential lacks scope | Emit `fetch_status: partial`, skip impacted fields. |
| Target not found | Abort with clear error. |
| Rate limited | Single retry after backoff. Never loop. |
| Adapter-specific failures | ... |

## Freshness

State how fresh this adapter's data can be:
- Source update cadence (e.g., "GitHub traffic updates hourly")
- Any lag between real events and when they appear in the API
- Recommended cadence for pulling (daily? weekly? on-demand?)

This feeds `/canvas-health`'s staleness detection.

## Theory grounding (optional but encouraged)

- Goodhart: which fields are vanity and must be paired with ratios?
- Gilad: what evidence does this replace (prior manual reporting)?
- Any adapter-specific rationale?
