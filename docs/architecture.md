# Architecture — how Mycelium is built and connected

**Audience**: contributors and integrators who need the whole picture in one place.
**Time to read**: 10 min.
**Last updated**: 2026-07-30.

Until now the architecture lived in five places (`CLAUDE.md`, the engine/harness READMEs, `context-surface.md`, `README.md`, `install-paths.md`). This file is the single map; each section points at the canonical detail rather than restating it.

## What Mycelium is

> Mycelium is a harnessing system for AI-assisted product development. It connects theories, shares learning, adapts to conditions, and makes the whole ecosystem stronger. (`CLAUDE.md`)

A **harness**, in Birgitta Böckeler's sense (`plugins/mycelium/harness/README.md`), is *"scaffolding that constrains an AI agent's behavior through a mix of computational enforcement (hooks, scripts) and inferential guidance (instructions, checklists)."* That two-part definition — **computational** + **inferential** — is the load-bearing distinction for everything below, and the axis along which the v0.20.0 plugin migration once split (see "The context surface").

## The building blocks and how they relate

```
                        ┌─────────────── engine (the brain) ───────────────┐
   user + agent  ◄────► │ diamonds · scales L0–L5 · theory gates · routing  │
                        └───────────────────────────────────────────────────┘
                                   │ constrained by            │ operates on
                                   ▼                           ▼
             ┌──────── harness (keeps it honest) ────┐   ┌──── canvas (state) ────┐
             │ 38 guardrails, 3 tiers:               │   │ .claude/canvas/*.yml    │
             │  BLOCK  → enforced by hooks (compute) │   │ source of truth,        │
             │  REVIEW → gate progression            │   │ committed to git,       │
             │  NUDGE  → advisory (inferential)      │   │ evidence not assumption │
             └───────────────────────────────────────┘   └─────────────────────────┘
                                   │ invoked as /mycelium:<name>
                                   ▼
                        ┌──────── skills (operations) ─────────┐
                        │ 60 skills, auto-loaded from SKILL.md │
                        └─────────────────────────────────────┘
```

| Layer | Role | Lives in | Böckeler half |
|---|---|---|---|
| **Engine** | Decision logic: diamonds, scales, theory gates, confidence, routing | `plugins/mycelium/engine/` | — |
| **Harness** | 38 guardrails in three tiers (BLOCK / REVIEW / NUDGE) that keep the agent honest | `plugins/mycelium/harness/` | both |
| **Hooks** | Event-fired scripts; computational enforcement of BLOCK-tier guardrails + feedback loops | `plugins/mycelium/hooks/` (`hooks.json`) | computational |
| **Skills** | 60 skills, invocable as `/mycelium:<name>`, auto-discovered from SKILL.md frontmatter | `plugins/mycelium/skills/` | inferential |
| **Canvas** | Source-of-truth product **state** (YAML), committed to git | the user's `.claude/canvas/` | — |
| **Domains** | Per-phase context overlays (discovery / delivery / quality) | `plugins/mycelium/domains/*/CLAUDE.md` | inferential |
| **Schemas** | Validation contracts for canvas YAML | `plugins/mycelium/schemas/` | computational |
| **Orchestration / JiT tooling / integrations / templates** | Multi-agent modes, stack auto-detection, cross-agent shims, starters | respective `plugins/mycelium/` dirs | — |

The relationship in one line (`plugins/mycelium/engine/README.md`): *"The engine never acts alone — it works with the harness (constraints), the canvas (state), and skills (operations)."* Detail: `engine/README.md`, `harness/README.md`.

## The runtime model

Two axes, taught by example in `docs/mental-model.md`:

- **Scales (L0–L5)**: Purpose → Strategy → Opportunity → Solution → Delivery → Market. L0–L3 are product-agnostic; L4–L5 adapt to `product_type`.
- **Diamonds**: every scale runs the same four phases — **Discover → Define → Develop → Deliver** — with **theory gates** between phases. You cannot progress a diamond by asserting confidence; you must show evidence that satisfies each gate (`engine/theory-gates.md`, `engine/diamond-rules.md`).

## The context surface — what reaches a session, and when

This is the part most worth understanding, and the part a migration can silently break (it did — see the v0.58.0 changelog entry). Full map: `docs/context-surface.md`.

**Always-on (every session):**
- The **agent operating contract** — `plugins/mycelium/engine/agent-operating-contract.md`, injected by the `SessionStart` hook (`hooks/session-start.sh`). This carries the always-on inferential rules (Communication Rules + the Mandatory Pre-Task / Pre-Ship / Post-Task Protocols). It is the plugin-form delivery path for rules that legacy `degit` installs used to template into each project's `.claude/CLAUDE.md`. Guarded by CI Check 47 and `tests/bash/test_session_start_contract_delivery.sh`.
- Dynamic feedback-loop reminders + corrections count (same hook), when overdue loops exist.
- Skill names + one-line descriptions (auto-discovered), and the user's project `CLAUDE.md` + auto-memory.

**Just-in-time (loaded when relevant):**
- Domain context (`domains/{discovery|delivery|quality}/CLAUDE.md`) per active phase.
- Engine / harness reference docs, canvas files, and each skill's full SKILL.md — read on demand, not front-loaded.

The design intent: the always-on surface stays **lean** (the turn-1-and-turn-30 behavioral contract); heavy reference is JiT. Computational enforcement (hooks) fires regardless of the model or session state; inferential guidance must be *delivered* to bind — which is why the contract is injected rather than assumed.

## Packaging, authoring, release, install

- **Form**: a Claude Code **plugin** (canonical since v0.20.0). Framework reference content lives in the plugin cache, addressed via `${CLAUDE_PLUGIN_ROOT}`; the user's `.claude/` holds **only project state**. Legacy `npx degit` is non-functional — it lands an empty `.claude/`. Removal was planned for v0.21.0 and did not happen; the tree is unmaintained. See [install paths](install-paths.md). Detail: `docs/install-paths.md`.
- **Descriptors**: `.claude-plugin/marketplace.json` (marketplace `haabe-mycelium`) → `plugins/mycelium/.claude-plugin/plugin.json` (the plugin manifest, carries `version`). `plugins/mycelium/manifest.yml` classifies every file `framework` (safe to replace) vs `project_state` (never overwrite).
- **Version discipline** (`plugins/mycelium/engine/version-discipline.md`): the `CLAUDE.md` Version line is the single source of truth; a bump is an atomic commit of `CLAUDE.md` + `plugin.json` + `docs/changelog.md` (+ derived docs via `sync_derived.py`). CI Checks 26/30/40 enforce it.
- **Release**: merge to `main` → CI (`validate.yml`) green → `auto-release.yml` reads the changelog section and creates the tag + GitHub Release.
- **Install**: `/plugin marketplace add haabe/mycelium` → `/plugin install mycelium@haabe-mycelium` → `/mycelium:start`. Update via `/plugin update`.

## Quality gates (what keeps it consistent)

`tests/validate-template.sh` (structural integrity, 47 checks incl. G-V12 test-coverage of checks, plus ruff/shellcheck/pytest and the bash tests via `tests/bash/run.sh`), `scripts/validate_canvas.py` (schema + trace), `scripts/check_doc_references.py`, `scripts/check_legacy_paths.py`, `scripts/check_theory_fidelity.py`, and a per-file coverage floor. They run in CI (`validate.yml`) and at push-time (the `pre-push` hook). **Dogfood runs from a consumer repo** (mycelium-roadmap), because a framework-repo-only check cannot see delivery/packaging gaps — the lesson behind Check 47 and the consumer-delivery test.

## Where the canonical detail lives

- Runtime model taught by example → `docs/mental-model.md`
- Exact context/load map → `docs/context-surface.md`
- Why it's opinionated → `docs/philosophy.md`
- Install forms + migration → `docs/install-paths.md`, `docs/migration.md`
- Engine internals → `plugins/mycelium/engine/README.md`
- Harness internals + guardrail tiers → `plugins/mycelium/harness/README.md`
- Always-on rules → `plugins/mycelium/engine/agent-operating-contract.md`
