# JIT tooling

**Audience**: practitioners using Mycelium on non-default tech stacks or non-software product types.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

Mycelium does not pre-ship a per-stack catalog of validation. It detects what is there and generates adapters. The discipline is JIT (just-in-time): zero handover from the framework's defaults to whatever you actually have.

## The detect-and-generate philosophy

The framework's north-star check is **zero handover** — a fresh project should not require the user to teach the framework what stack they use. The framework should figure it out from signals and ask only when it cannot.

This applies uniformly across:

- **Tech stacks** — `/delivery-bootstrap` detects language/framework from package files (`package.json`, `pyproject.toml`, `Cargo.toml`, `Package.swift`, etc.) and generates stack-appropriate validation.
- **Product types** — the detector classifies into `software`, `content_course`, `content_publication`, `content_media`, `ai_tool`, `service_offering` based on canvas signals + repo signals.
- **Metric sources** — `/metrics-detect` scans for git remote, SDK installs, env vars; asks about channels the repo cannot reveal (deployed URL, payment processor, app stores).

Pre-shipped catalogs would couple Mycelium to the assumptions of whatever was popular when the catalog was built. Detection survives platform shifts.

## `/delivery-bootstrap`

Runs at the start of a delivery diamond. Auto-detects the stack:

- Reads package manifests
- Reads `language` field in `purpose.yml` if set
- Falls back to git history (most-recent file types)
- Asks the user only when it cannot disambiguate

Generates:

- Validation runner adapter (test command, lint command, type-check command)
- Bootstrapped ADR scaffolding if architecture decisions are needed
- Pre-commit and definition-of-done checklist scoped to the stack

See `.claude/jit-tooling/detector.md` for detection rules.

## `/metrics-detect`

The metrics-harvesting equivalent. Scans for:

- Git remote → GitHub adapter
- Plausible / Google Analytics / Fathom env vars or scripts → web analytics adapter
- Stripe / Paddle keys → payment adapter
- App Store Connect / Google Play credentials → mobile-app-store adapter
- LinkedIn / X / community Slack signals → reach adapter (manual entry, structured)

The detector asks about channels it cannot infer (deployed URL, app store IDs). Generates an `active-metrics.yml` with the configured sources. Then `/metrics-pull` snapshots them and writes timestamped, sourced evidence into canvas files.

This converts "I checked the dashboard" into diffable evidence with confidence and provenance — same shape as user-research evidence.

## `product_type` dimension

The framework's L4–L5 work is product-type-aware:

- **software**: DORA + APEX, OWASP, SoC, threat model, accessibility per WCAG 2.1 AA
- **content_course**: completion rate, learner engagement, content-specific definition of done
- **content_publication**: read-through, citation, content-specific quality gates
- **content_media**: viewer engagement, distribution-channel metrics
- **ai_tool**: APEX-shaped DORA + xai-check + system card requirements
- **service_offering**: Downe's 15 service principles weight, service blueprint, customer journey

The detector classifies once at L4 entry; the user can override. Subsequent L4–L5 gates check the right things for that type.

## Why this is non-negotiable for Mycelium

The corrections log shows that the framework drifts toward whatever the founder is building right now. If Mycelium pre-shipped a per-stack catalog, that drift would compound — the catalog would over-fit to the dogfood projects.

JIT detection externalizes the stack-specific knowledge to the moment of need. The framework's contribution is the detection rules and the adapter shape; the stack-specific content is generated at use time. This is the same pattern as the canvas (validation contract before content) and the cluster log (spec before mechanism).

## See also

- `.claude/jit-tooling/detector.md` — full detection rules
- [usage-modes.md](usage-modes.md) — JIT tooling integrates into all modes
- [skills/README.md](skills/README.md) — `/delivery-bootstrap`, `/metrics-detect`, `/metrics-pull`
