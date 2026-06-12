# Render Conventions

Canonical conventions for skills that emit visual or structured renderings of canvas state, memory, or other Mycelium project state.

All `/mycelium:<x>-render` specialist skills and the `/mycelium:render` dispatcher read this document. Conventions are mechanically enforceable where a Validator check ships (Check 43 covers identifier-exposure declaration); the rest are prose discipline reviewed at upstream promotion.

## HARD RULE: Consent + privacy gate

Before any render skill emits output containing canvas fields that may hold personal identifiers, it MUST consult the attribution registry and redact entries whose consent state does not permit the render's audience.

This rule is non-skippable. A render that leaks a tester's name (or any identifier they did not consent to publish) is a privacy incident. The canvas treats consent as load-bearing state per the consent-state-change-skip cluster (anti-pattern #7 sub-shape, instance #15, 2026-06-02). Surfacing redaction at render time is the same discipline `/mycelium:log-evidence` 8c(d) safety net applies at write time.

### Registry path resolution

- **Preferred**: `$MYCELIUM_ATTRIBUTION_REGISTRY` environment variable.
- **Fallback**: `.claude/memory/attribution-registry.yml` (registry lives in roadmap-private memory by design — upstream-public repos must not ship the registry).
- **Absent**: fail-open with a render-header warning `⚠ no attribution-registry — consent-redaction not enforceable; treat output as roadmap-internal`.

### Registry schema (real, verified)

```yaml
people:
  - name: "Drew"           # first-name disambiguation
    consent: public_ok     # or generic_only | unknown
    note: |                # optional prose carve-out
      Explicit consent for public attribution given prior to inclusion.
```

### Consent value semantics

| Value | Render behavior |
|---|---|
| `public_ok` | Render literal. Covers academic-citation public figures AND individuals who gave feedback in public/effectively-public channels. |
| `generic_only` | Redact to anon-label. Identity allowed in roadmap-private artifacts; MUST be generic-framed in upstream-public artifacts. |
| `unknown` | Treat as `generic_only` per registry README (consent unverified ⇒ conservative). |

Identifier not in registry → fail loud. The only override is `--no-identifiers=true` which forces ALL names to redact regardless of consent state.

### Anon-label convention

- Cohort tester → `cohort-tester-N`
- Peer practitioner → `peer-practitioner-N`
- Maintainer / employee → `maintainer-N` or `employee-N`
- Unknown class → `participant-N`

Numbering is consistent across a single render (same registry entry → same N). For dispatcher cross-cutting views: numbering is shared across canvas activations (cohort-tester-2 in cycle-003 IS cohort-tester-2 in opp-004 evidence).

### Carve-out notes (registry `note:` field)

When emitting a name whose registry entry has a non-empty `note:`, append a footnote pointer (`see registry note for <name>`) in the render's audit-footnote block. The render skill cannot mechanize carve-out enforcement (free-form prose requires human judgment); the pointer ensures the operator reads the carve-out before publishing.

Canonical example: "Frida" is `consent: public_ok` for the name BUT her project name has a hard carve-out. The render emits "Frida" literally and points the operator at the registry note to confirm the project-name rule before external publication.

### Audience tier maps to consent tier

| Audience (set via `--audience` or skill default) | Required consent tier |
|---|---|
| `founder` (terminal, private) | any (founder already has access) |
| `cohort` (Claude Code session, semi-private) | `public_ok` literal, `generic_only` redacted |
| `external` (GitHub, receipts case, mermaidchart.com paste) | `public_ok` literal only; `generic_only` redacted |

Default audience: `cohort` when `--audience` unspecified. Specialists override per their own discipline.

### Specialist declaration requirement (Check 43)

Every render specialist (skill name ends in `-render`) and the dispatcher MUST declare `identifier_exposure` in frontmatter:

```yaml
metadata:
  identifier_exposure: "YES"   # or NONE | MIXED
```

The skill MUST also include a `## Identifier exposure` body section per the §15 canonical structure (Declared / Scope / Rationale / Anon-label convention / Worked examples / Fixture pointer). MIXED declarations MUST include a per-canvas table.

Check 43 (in `tests/validate-template.sh`) mechanically enforces frontmatter presence + value + body-section first-line consistency on every shipped render skill.

## Supported formats

| Format | When | GitHub-renders | Terminal-renders | Lossy on data |
|---|---|---|---|---|
| `mermaid` | default; share with humans | yes | no (raw text only) | mid (structure preserved; metadata dropped) |
| `ascii` | terminal-first; founder dogfood | yes (as code block) | yes | high |
| `markdown-table` | tabular data, comparison views | yes | yes | high (loses non-tabular shape) |
| `markdown-list` | hierarchical fallback | yes | yes | mid |
| `json` | external-system integration | yes (as code block) | yes | none on data (lossy on prose only) |

**On `json` audience scope**: JSON is for external systems (BI tools, dashboards, third-party integration), NOT for agent-to-agent consumption. Mycelium agents read the canvas YAML directly. JSON is the only format that round-trips structured data losslessly.

## Format × audience decision matrix

When `--format` is unspecified, agent consults the matrix:

| Audience ↓ / Format → | mermaid | ascii | markdown-table | markdown-list | json |
|---|---|---|---|---|---|
| founder (terminal) | secondary | **default** | secondary | secondary | wrong-shape |
| cohort (Claude Code session) | **default** | secondary | secondary | secondary | wrong-shape |
| external (GitHub, receipts) | **default** | wrong-shape | secondary | secondary | secondary |
| external-system (BI, dashboard) | wrong-shape | wrong-shape | secondary | wrong-shape | **default** |
| agent-to-agent | NEVER (read canvas YAML directly) | NEVER | NEVER | NEVER | NEVER |

Cells:
- **default** — skill picks this when `--format` unspecified and audience is known
- **secondary** — skill accepts if explicitly requested
- **wrong-shape** — skill REFUSES with the unsupported-format fail-loud message
- **NEVER** — skill never renders for this audience; the canvas YAML is the agent contract

## Format-support negotiation (global rule)

Not every format is supported by every specialist. The agent consults the specialist's `## Arguments` table for the supported set:

- If `--format <X>` is supported → proceed.
- If unsupported (e.g., `diamond-render --format markdown-table` — state diagrams don't map to tables) → **fail loud** with: specialist name, supported formats for this specialist, one-line explanation of why the requested format doesn't fit, pointer to the closest fit.
- **Never** silently downgrade. Silent fallback hides the mismatch from the user.

## Mermaid frontmatter syntax (preferred)

The `%%{init: ...}%%` directive syntax is **deprecated** as of Mermaid v10.5.0. Render skills emit configuration via **frontmatter YAML**:

```yaml
---
config:
  theme: base
  themeVariables:
    primaryColor: '#ffffff'
    primaryTextColor: '#1a1a1a'
---
```

When porting older render output to current skills, migrate from `%%{init: ...}%%` to `--- config: ... ---`. The init directive may still work in some renderers but is not the supported form.

## WCAG AA theme convention

Render-fleet output is human-audience by definition; WCAG AA contrast (4.5:1 for normal text, 3:1 for large text) is the right bar. Two paths to AA compliance, in order of preference:

### Path A: `theme: dark` (simplest)

Mermaid's built-in `dark` theme passes WCAG AA by construction. Specialists offer `--theme dark` opt-in. Use when the operator wants the smallest possible config and the target audience is dark-mode-compatible.

```yaml
---
config:
  theme: dark
---
```

### Path B: `theme: base` + explicit palette (light + dark portable)

For light-mode-dominant audiences (GitHub README, receipts cases), use `theme: base` with explicit `themeVariables`:

```yaml
---
config:
  theme: base
  themeVariables:
    # diagram-type-specific keys per the table below
---
```

### Diagram-type → theme-variable mapping

| Diagram | Working keys | Notes |
|---|---|---|
| `stateDiagram-v2` | `primaryColor`, `primaryTextColor`, `primaryBorderColor`, `lineColor` + `classDef <name> fill:#x,stroke:#y,color:#z` for highlight states | `classDef` is required when `class <X> <name>` is used; without it the class line is a silent no-op |
| `mindmap` | `cScale1`-`cScale7` (section fills) + `cScaleLabel1`-`cScaleLabel7` (text per section) + `git0` (root fill) + `gitBranchLabel0` (root text) | Off-by-one: `cScale0`/`cScaleLabel0` are wasted (section indexing starts at cScale1). The keys are undocumented but source-verified (see `packages/mermaid/src/diagrams/mindmap/styles.ts`). `primaryColor` does NOT control mindmap. |
| `gantt` | `sectionBkgColor`, `altSectionBkgColor`, `doneTaskBkgColor`, `doneTaskBorderColor`, `activeTaskBkgColor`, `activeTaskBorderColor`, `critBkgColor`, `critBorderColor`, `taskTextColor` (+ Dark/Outside/Light variants) | `:crit` reads as "failure" visually — surface as a UX caveat in specialist docs |
| `pie` | `pie1`-`pie12`, `pieTitleTextColor`, `pieSectionTextColor`, `pieLegendTextColor`, `pieStrokeColor`, `pieOuterStrokeColor` | Standard documented theme variables |
| `flowchart` | `primaryColor`, `primaryTextColor`, `primaryBorderColor`, `lineColor`, `clusterBkg`, `clusterBorder` | Standard documented variables; classDef supported |

### Verified working palette (Material Design + paired text contrast)

For `theme: base` themeVariables, the following palette is verified-working across mermaid.live, mermaidchart.com, and Obsidian:

```yaml
# Mindmap palette (cScale1-7 with paired text contrast per fill)
cScale1: '#42A5F5'  ; cScaleLabel1: '#FFFFFF'   # blue + white
cScale2: '#66BB6A'  ; cScaleLabel2: '#000000'   # green + black
cScale3: '#EF5350'  ; cScaleLabel3: '#FFFFFF'   # red + white
cScale4: '#AB47BC'  ; cScaleLabel4: '#FFFFFF'   # purple + white
cScale5: '#26A69A'  ; cScaleLabel5: '#000000'   # teal + black
cScale6: '#FFA726'  ; cScaleLabel6: '#000000'   # orange + black
cScale7: '#8D6E63'  ; cScaleLabel7: '#FFFFFF'   # brown + white
git0: '#FDD835'     ; gitBranchLabel0: '#000000' # root yellow + black
```

All combinations exceed 4.5:1 AA contrast; most exceed 7:1 AAA.

### Limit: agent cannot visually validate (partially mechanized)

The agent emits Mermaid syntax but cannot visually evaluate the rendered diagram. The two deterministic checks the agent cannot do by eye are now mechanized — **`scripts/validate_mermaid.py`** statically audits (1) WCAG AA contrast of every `themeVariables` foreground/background pair (closes the F13 contrast blind-spot — contrast ratio is pure math, no rendering surface needed) and (2) state-id consistency (closes F11). Pipe the emitted block to it: `printf '%s' "$DIAGRAM" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_mermaid.py -` (add `--cli` to also shell out to `mmdc` for a full parse when the binary is present — fail-open when absent). What remains genuinely operator-side is **visual layout / communicative quality** (does the diagram read well, is the information ordering right) — that judgement still needs a human eye, so specialists keep "render output should be visually inspected before external publication" in their canonical disclaimer. Coverage proof: `tests/bash/test_validate_mermaid.sh`.

## Mermaid label-escape rules

- Quote any label containing `:`, `(`, `)`, `[`, `]`, `<`, `>`, `|`.
- Replace embedded double-quotes with `#quot;`.
- Replace embedded `<br>` line wraps with explicit `<br/>`.
- Truncate labels >60 chars; append `…` and full text in a footnote.

## Mermaid state ID consistency (Check via Counter-Argument)

For diagrams with explicit state-ID declarations (`state ... as <ID>`), every `<src> --> <dst>` arrow and every `class <X> <name>` line MUST reference a defined state ID OR a Mermaid built-in (`[*]`). Mismatch produces a parse error at render time and is unverifiable from the syntax alone.

Specialists include this check in their Counter-Argument block. Render-time syntactic validation is now mechanized — `scripts/validate_mermaid.py` enforces this state-id rule (plus WCAG contrast) statically with no external dependency; `--cli` adds an `mmdc` full-parse cross-check when available. Run it on the emitted diagram before external publication.

## Schema versioning + graceful degradation

Canvas schemas evolve. Render skills should:

- **Ignore unknown fields silently.** A field the renderer does not know about is out-of-scope, not lost; NOT listed under `dropped_fields` (which means "known but format can't carry").
- **Treat renamed fields as missing.** If `opportunities.yml#opportunity.title` becomes `headline` in a future schema and the specialist still reads `.title`, the render shows the entry without a title rather than crashing. Surface as `(no title set)`.
- **Treat deprecated fields as still readable** for at least one minor version after deprecation.
- **Surface schema-version mismatch** in the render header when the canvas's `schema_version` exceeds what the specialist was written against: `⚠ canvas schema_version 2; renderer expects 1 — fields may be missing from output`.

## Lossy-on-export template

Append to every render output:

> _Render is a static snapshot; canvas remains source of truth.
> Fields not surfaced in this view: \<comma-separated list of dropped fields>._

## Beta-format warning template

Prepend to outputs using a beta keyword:

> _Renders Mermaid `<keyword>` (beta). Syntax may shift in future Mermaid releases; canvas data unaffected._

Examples: `wardley-beta`, `xychart-beta`, `sankey-beta`, `radar` (beta as of 2026-06-07).

## Canonical disclaimer

Every render skill emits this as the final block:

> _Render: `<skill-name>` v`<framework-version>`. Source: `<canvas-file-path>`. Canvas state as-of: `<canvas-_meta.last_validated>`. Format: `<format>`._
>
> _For interactive editing or shareable URL, paste Mermaid blocks at https://mermaidchart.com (external dependency; no Mycelium affiliation)._

Notes on the fields:

- `<framework-version>` lets receipts cases that embed rendered output pin the skill version (a v0.40.5 render is not silently confused with a v0.40.0 render).
- `<canvas-_meta.last_validated>` is the canvas file's timestamp, NOT wall-clock. The render reflects canvas state as-of validation; if validation is stale, the render is stale.
- mermaidchart.com handoff omitted for `--format ascii`, `--format json`, and any future non-Mermaid format.
- If a staleness warning fired per the specialist's staleness check, it prepends the disclaimer.

## Canvas-state timestamp resolution

Specialists read the timestamp in this order:
1. `_meta.last_validated` if present.
2. Top-level `last_updated:` field as fallback.

`diamonds/active.yml` currently uses `last_updated:` at file root; other canvases use `_meta.last_validated`. Spec accepts both. Canvas-side normalization is a separate `/mycelium:canvas-health` concern.

## Staleness check distinction

Two failure shapes that both involve "canvas timestamp older than recent activity":

- **Canvas-stale**: a recorded field drifted from decision-log entries (correction-after-the-fact, gate-status change). Use `⚠ STALE: <file> last updated <date>; decision-log activity for <topic> since (entry <date>). Render reflects canvas state, not the unrecorded movement.`
- **Pending-retrospective** (specific to cycle-render): decision-log has substantive work since the last `completed_at` but no cycle entry yet. The canvas data isn't wrong; there's session work pending retrospective. Use `ℹ Pending retrospective: decision-log activity since <file>'s most recent <entry-type> (<entry-id> completed <date>). Running /mycelium:retrospective will fold it in. Render reflects closed-and-recorded; in-flight session work is intentionally absent.`

The first is a warning; the second is informational. Render proceeds in both cases.
