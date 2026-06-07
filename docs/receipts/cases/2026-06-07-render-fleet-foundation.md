---
id: 2026-06-07-render-fleet-foundation
date: 2026-06-07
contributor: Håvard Bartnes (founder, dogfood-session catch)
contributor_link: CONTRIBUTORS.md
project: mycelium-roadmap (private; the dogfood project where four sessions of render-fleet iteration surfaced thirteen findings before upstream promotion)
mechanism_or_status: shipped. v0.40.0 lands the engine convention doc, the first specialist (`/mycelium:diamond-render`), and Validator Check 43 mechanically enforcing identifier-exposure declaration on the render-fleet skill class. Three more specialists follow in v0.40.1–v0.40.3 patches as they stabilize.
commits: [pending v0.40.0 commit hash]
subclass: dogfood-discipline-protected-upstream
---

# render-fleet-foundation: thirteen findings the dogfood caught before they shipped

**Audience**: contributors and operators interested in how Mycelium's dogfood loop protects upstream promotion. Also: anyone curious why a four-skill feature ships its foundation as the smallest possible upstream commit instead of all at once.
**Time to read**: 7 min.
**Last updated**: 2026-06-07.

## The trigger

Thirteen architectural findings, four dogfood sessions, one upstream surface kept clean. The order of those numbers is the whole point of this case.

Simon Wardley's LinkedIn post 2026-06-07 mentioned OnlineWardleyMaps having absorbed into Mermaid's DSL. Verification showed Wardley map syntax landed in Mermaid v11.14.0 as `wardley-beta`. The session question quickly widened from "should `/mycelium:wardley-map` get a Mermaid export?" to "what's the right architecture for rendering Mycelium's canvas state at all?"

A deep-dive surfaced 25 canvas files, one active diamond file, structured memory, an event stream. Almost none of it visualized today. The architecture draft `.claude/drafts/render-skill-architecture-2026-06-07.md` proposed a hybrid: shared engine convention doc, central dispatcher, per-canvas specialist children. Phase 1 through 4 ship plan: draft each specialist dogfood-local in the roadmap repo, exercise against this project's actual canvas, surface friction, promote upstream only after the design stabilized.

Four dogfood sessions later, thirteen findings had been logged and fixed before any upstream commit. This case documents what was caught.

## The findings

Each finding got an F-number, was logged in the draft, fixed in the SKILL.md, and where applicable propagated to the evaluator and auto-dogfood scenarios. Compressed list:

**F1–F4: diamond-render spec drift vs canvas (Phase 1 exercise).** The spec assumed `_meta.last_validated` for canvas timestamp, lowercase-vs-canonical phase names, gate vocabulary clarity, and a spawn-arrow convention. The actual canvas used `last_updated:` at file root, lowercase phase values, two distinct gate concepts (phase-transition vs theory), and no spawn-arrow convention at all. All four resolved by reading the canvas first.

**F5–F7: registry path + schema + carve-out semantics (Phase 2 exercise).** The spec said `.claude/attribution-registry.yml`. The actual registry lives at `.claude/memory/attribution-registry.yml`, accessed canonically via `$MYCELIUM_ATTRIBUTION_REGISTRY` env var because it must not ship to the public upstream repo. The schema differed too. The spec used `entries: + identifier: + consent: granted|pending|declined + public_ok: bool`. The actual schema is `people: + name: + consent: public_ok|generic_only|unknown` with optional prose `note:` carve-outs. The orchestrator extension, four auto-dogfood scenarios, and twenty test cases all carried the fake schema; coupled-fix landed before ost-render shipped.

**F8: maintainer self-reference not in registry.** Strict spec said fail-loud on every name absent from the registry. Håvard's own first name appears in cycle-008's learnings and dozens of canvas surfaces. Fix: add the maintainer as `consent: public_ok` with a self-reference note. The registry's first explicit entry for the person whose name is on the commits.

**F9: verbose mode for cycle-render, pros/cons deep dive, no ship.** The temptation was to add a `--verbose` flag surfacing `learnings.process` prose blocks. Cons (consent-check scope explosion, Mermaid label-escape strain, render volume explosion, poorly-bounded "verbose" semantics) outweighed pros. Decision: ship none of the alternatives today. Add `--include-learning <field>` to open-implementation-questions with N=2-asks-in-30-days promotion trigger.

**F10: staleness vs pending-retrospective distinction.** Decision-log activity newer than cycle-history's most-recent `completed_at` is not staleness. The canvas data isn't wrong; there's session work pending retrospective. Fix: two distinct message shapes. `⚠ STALE` for canvas drift, `ℹ Pending retrospective` for unrecorded session work.

**F11: Mermaid syntactic validity unverified.** The agent emitted a spawn arrow using canvas IDs (`l0-purpose --> l1-strategy`) instead of the Mermaid state IDs (`L0 --> L1`) defined in the `state ... as L0` declarations. Parse error at the user's render. Mitigation: discipline-only pre-emit checks (Counter-Argument items 3 and 4); mechanical `mmdc --validate` deferred until 2nd instance reaches the user.

**F12 / F13: WCAG accessibility, four-attempt arc.** The first OST mindmap rendered with rotating background colors and white text. Multiple node blobs unreadable. The agent's diagnosis went through four attempts before reaching the right answer:

1. *"Mindmap is uncontrollable; switch to flowchart TD."* Wrong. Too structural a response.
2. *"Use `themeCSS` with `.mindmap-nodes .section-N` selectors per Obsidian forum."* Wrong. `themeCSS` is sanitized by some renderers; not the canonical path.
3. *"Read `styles.ts`; the `cScale*` family is the truth."* Half-right. Those variables work but are undocumented; documented API alone is insufficient for mindmap WCAG.
4. *"Frontmatter syntax replaces deprecated `%%{init:...}%%`; `theme: dark` passes WCAG by construction; `theme: base` + paired cScale palette works portably."* Final.

Each operator redirect surfaced something the previous attempt missed. The pattern was consistent: the agent reached for the most complex plausible solution before trying the simplest. Each attempt added layers when the actual right answer was simpler. Try `theme: dark` first. If needed, set `theme: base` + minimal variable overrides. Use frontmatter syntax. The simpler approach was always available; the agent did not take it because each redirect made the prior failure feel like *now I know better*. The expert mode is unfortunately the failure mode.

## What v0.40.0 actually ships

The instinct after thirteen findings was *ship all four specialists at once now that they're stable*. The discipline pushed back. v0.40.0 lands the smallest coherent foundation:

- **`engine/render-conventions.md`**: the shared convention doc that all render skills read. Encodes every F1–F13 lesson at the right altitude. HARD RULE consent + privacy gate at the top. Format × audience decision matrix. WCAG AA theme convention with per-diagram-type variable mapping including the F13-corrected mindmap `cScale*` cells. Frontmatter syntax as the supported form. Canvas-state timestamp resolution + the staleness-vs-pending-retrospective distinction. Canonical disclaimer template.
- **`/mycelium:diamond-render`**: first specialist. NONE identifier exposure, smallest interface surface, no consent-gate complexity. The lowest-risk first promotion.
- **Validator Check 43**: mechanically enforces `identifier_exposure: YES|NONE|MIXED` frontmatter + `## Identifier exposure` body section on every render-fleet skill (name pattern `*-render` or exact `render`). Three failure modes named explicitly. Five fixtures + eleven test assertions cover missing frontmatter, invalid value, missing body, valid YES, valid NONE.

Three more specialists wait. `/mycelium:ost-render` and `/mycelium:cycle-render` carry YES exposure and active consent-gate machinery; they ship as v0.40.1 and v0.40.2 patches as each stabilizes. `/mycelium:render` dispatcher ships as v0.40.3. The cross-cutting `--view traceability` view stays deferred to Phase 4a–4d research-first methodology per architecture draft §10.2. The framework intentionally does not emit a *best guess* cross-canvas view to avoid teaching users to think with a shape that was not visually validated.

## What this case taught the framework

Three lessons, each grounded in the artifact rather than the intent:

1. **Dogfood-local before upstream is load-bearing for render-fleet feature-class work.** Thirteen findings in four sessions is high friction. Most were architectural, not cosmetic. Each one would have shipped as a downstream bug if the work landed upstream directly. The discipline of *roadmap-local first, upstream after stability* is the gate that caught them.
2. **Documented API and source code each tell a partial truth.** F13 went through four attempts because the agent treated each single source as authoritative. The actual answer required holding multiple sources in tension. The documented theming page omits mindmap-specific variables. The source code uses undocumented `cScale*` variables. The directives docs mark `%%{init:...}%%` deprecated. Empirical render testing proves what actually works in the target renderer. No single source gave the right answer alone.
3. **Incremental promotion bounds the blast radius.** Shipping the engine doc plus one specialist plus the validator check first is smaller than shipping all four specialists at once. If a Phase 4 promotion regresses for an external installer, only the foundation moves; the other specialists wait. The receipts case ships with v0.40.0 so the friction trail is public from day one rather than reconstructed later.

## Mechanism + status

**Status**: shipped. v0.40.0 lands `engine/render-conventions.md`, `plugins/mycelium/skills/diamond-render/`, Validator Check 43 (with 5 fixtures + 11 test assertions), `CLAUDE.md` version bump, `plugin.json` version bump, `docs/ai-system-card.md` skill-count sync via `sync_derived.py`, and this receipts case. The 41 prior Validator checks still pass. Check 43 newly passes on the shipped diamond-render skill.

**Deferred to v0.40.1+**: `ost-render` (YES exposure, consent gate active). `cycle-render` (YES exposure, gantt + pie + json). `render` dispatcher (MIXED, recommends-not-invokes, cross-cutting traceability research-gated to Phase 4a–4d).

## Attribution note

Sources cited inline: the architecture draft `.claude/drafts/render-skill-architecture-2026-06-07.md` in the roadmap repo (public via the haabe/mycelium-roadmap repository); the Wardley LinkedIn post 2026-06-07 that triggered the wider session question; the Mermaid documentation and source code at github.com/mermaid-js/mermaid that resolved F13. The F1–F13 friction trail was generated by Håvard exercising each draft specialist against this project's actual canvas, opportunities, and cycle history. Maintainer self-reference handling per F8 added Håvard to the attribution registry as `consent: public_ok`, the registry's first explicit maintainer entry.

The render fleet caught itself thirteen times before its first upstream commit. Thirteen architectural findings, four dogfood sessions, one upstream surface kept clean. The order of those numbers is the discipline working at the altitude it was built for.
