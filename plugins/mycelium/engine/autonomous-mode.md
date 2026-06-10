# Autonomous mode

The pattern for running Mycelium with **no person in the loop** — headless sessions, scheduled agents, agent-to-agent dogfood runs. Autonomous mode answers one question the framework previously left undocumented: *who answers when a skill addresses a question to the human, and nobody is there?*

Sibling of `dogfood-mode.md`, orthogonal to it: dogfood mode reframes **what failure means** (a killed diamond becomes a learning); autonomous mode reframes **who answers** (a declared substitution stands in for the absent human). The two compose — the canonical automated dogfood run is both — but neither implies the other. Dogfood mode never authorizes substituting human input; this doc is the only place that authority comes from.

Evidence base: Fable 5 dogfood evaluation 2026-06-11 (opp-011 in `canvas/opportunities.yml`; receipts case `docs/receipts/cases/2026-06-11-fable5-autonomous-run.md`). A desk audit of all 54 skills found exactly 5 blocking interaction points with documented non-interactive fallbacks; a headless run then completed the full minimal path (start → brief → assumption-test → diamond-assess) only because its run prompt pre-authorized the substitution ladder below. This doc graduates that improvised rule to framework mechanism.

## Declaration — autonomous mode is consent, not detection

Autonomous mode applies **only when explicitly declared**. Two surfaces:

1. **Run-prompt declaration** (canonical for headless runs; required when no project state exists yet). The launching operator's prompt must state: autonomous mode is active, the mocked persona to answer as (if any), the intended skill path/scope, and the ledger path. This prompt is the consent artifact — the human pre-authorization that delegation-authority requires for acting without per-decision approval.
2. **`autonomous: true` root-level flag in `.claude/diamonds/active.yml`** (durable record; sibling of the root-level `dogfood` flag). An autonomous run sets it at its first state write so later sessions and hooks can see the project carries autonomous-run state.

**Non-interactive detection alone NEVER activates autonomous mode.** A headless session without a declaration must stall honestly at blocking points (rung c below), not improvise — headless is a runtime condition, not consent. Conversely, **a present human always outranks the flag**: in an interactive session, ask the human even if `autonomous: true` is set.

## The substitution ladder

At every blocking interaction point (a question addressed to the user, a menu, a consent prompt, a "wait for the human" instruction), apply the first rung that fits, and ledger it:

- **Rung (a) — documented per-skill default.** The skill text itself documents a non-interactive default (e.g., setup's "Auto-mode default: … default to creating AGENTS.md when absent"). Apply it and quote the skill text in the ledger. Never claim rung (a) without a quotable documented default.
- **Rung (b) — persona self-answer, tagged.** Answer as the declared mocked persona. Every artifact derived from the answer is tagged `source_class: internal_simulated`, `evidence_type: speculation` (never higher), `validated: false`. Ledger entry mandatory: skill + step, blocking instruction quoted, the substituted answer, tags applied.
- **Rung (c) — honest HARD GATE.** Neither rung applies without crossing the evidence-integrity boundary or a human-only marker. Log the block in the ledger, leave the artifact in its honest blocked state (e.g., an assumption test stays `designed`, a diamond stays in phase), and continue to the next reachable step. A rung-(c) entry is correct output, not a run failure.

**Default-substitutable rule:** any interaction point NOT in the human-only registry below is rung-(b) substitutable when autonomous mode is declared. Skills do not need individual auto-mode notes for ordinary questions and menus; inline markers are reserved for gates needing special semantics (see per-skill table).

**Pre-commit ordering rule:** when rung (b) substitutes a pre-commitment (persona spectrum, stop condition, Rother-style prediction), write it to the ledger and decision log **before** generating any dependent content. Human authorship is substitutable; commitment-before-data is not — the ordering is the load-bearing part of the discipline.

## The substitution ledger (mandatory)

Every autonomous run maintains `.claude/evals/autonomous-run-log.md` — fixed path, so humans and hooks can answer "was this an autonomous run, and what got substituted?" without a directory scan. Append one dated section per run:

```markdown
## Run YYYY-MM-DD — <persona / scope one-liner>

### Substitution log
### N. <skill> — <step>
- Blocking instruction (quoted): "..."
- Rung applied: (a) documented default | (b) persona answer | (c) HARD GATE
- Substituted answer / mitigation: ...
- Tags applied: source_class: internal_simulated, validated: false  # rung (b)

### Self-audit — session end
- Deviations from skill text (numbered, complete)
- Substitutions by rung (full list; every rung-(a) claim quotes its documented default)
- Hard gates hit (rung (c) + harness blocks)
- Completion criteria: PASS/FAIL per criterion, with caveats stated plainly
```

The end-of-run self-audit is part of the run, not optional cleanup. `.claude/evals/*` is project state (not material framework files), so ledgers ride along without version-bump pressure.

## Evidence-integrity boundary (HARD RULE)

**Permitted:** self-answering interaction prompts addressed to the human — interview questions, depth menus, cognitive-forcing judgments, coaching answers, pre-commitments — as the declared persona, tagged per rung (b).

**Never permitted, in any mode:**
- Fabricating evidence the framework classifies as external: interview results, survey responses, user quotes, metrics, market signals. `external_human` and `external_data` mean a human or the world actually answered.
- Upgrading `evidence_type` on simulated material (it is `speculation`; mocked-persona-interview Rule 4 applies unchanged).
- Flipping `validated: true` on claims the run did not externally validate.
- Crossing a phase-confidence threshold on evidence that is internal_simulated-only.

The consequence: **evidence gates are expected to fail honestly in autonomous runs.** An autonomous run that ends "blocked on the Evidence gate; assumption test designed, awaiting real respondents" has succeeded. The 2026-06-11 run did exactly this — refused to simulate interview results, left its test in `designed` status — and that behavior is the contract, not a courtesy.

## Human-only registry (rung (b) forbidden — hard gates in autonomous mode)

Per `harness/delegation-authority.md` (no-standing list and BLOCK-equivalent rows), these are never self-answered:

| Gate | Source |
|---|---|
| Choose the bet — which opportunity/solution to pursue | delegation-authority no-standing #1 |
| Accept a security / privacy / regulatory / ethics tradeoff | delegation-authority no-standing #2 |
| Modify the authority map, guardrails, or this doc's rules mid-run | delegation-authority no-standing #3 |
| `/mycelium:diamond-progress kill` confirmation | destructive; kill stays human-confirmed |
| Phase-advance approval where `confidence-thresholds.yml#human_approval` says `required` | approval is the human's act; an agent approving itself is abdication-by-proxy |
| `/mycelium:migrate-from-legacy` "wait for explicit yes" | destructive migration of project state |
| `/mycelium:eval-runner` scenario retirement | destructive to eval history |
| `/mycelium:delivery-bootstrap` per-tool install consent | JIT tooling is nudge-not-push; consent to install is the user's |
| `/mycelium:metrics-detect` / `metrics-pull` configuration confirmations | configures external-source access |
| External outreach / publishing of any kind | delegation-authority REVIEW→BLOCK row |

Park and pivot remain available autonomously (reversible, evidence-driven, ledger + decision-log required). The escape hatch (`orchestration/escape-hatch.md`) is orthogonal and unchanged: emergency harm-reduction with payback log, not a way around this registry. Under uncertainty about whether a gate is registry-covered, round up to rung (c) — per delegation-authority, uncertainty is not a licence to act.

## Harness-permission story

Observed 2026-06-11 (run artifact, Stage 2): in headless mode the Claude Code harness auto-denied **every write under the project's `.claude/`** as "sensitive file" — across Bash, Write, cp, and filesystem-MCP — and rejected `$CLAUDE_PROJECT_DIR` expansion in Bash. The run's only true hard gate was the harness, not a Mycelium skill. An autonomous run must therefore plan its write path before launch:

1. **Primary path — operator pre-authorizes the state paths.** Before launching, add explicit allow rules to the project's `.claude/settings.json` (or `settings.local.json`) for the Mycelium state tree: `Write`/`Edit` on `.claude/canvas/**`, `.claude/diamonds/**`, `.claude/memory/**`, `.claude/harness/**`, `.claude/evals/**`, `.claude/jit-tooling/**`, plus the `Bash(mkdir …)` calls setup needs. *Unverified: whether an allowlist overrides the headless sensitive-file denial has not yet been tested — the 2026-06-11 run launched without these rules. Gated by: first autonomous run under this doc verifying the allowlist — interventional. That run's ledger must record the answer either way; update this section when it lands.*
2. **Mandatory write probe.** Step 0 of every autonomous run: attempt the ledger write (`.claude/evals/autonomous-run-log.md`). Success → canonical `.claude/` paths throughout. Denied → switch to the fallback immediately and record the probe result as the run's first ledger entry.
3. **Documented fallback — `mycelium-state/` mirror.** Mirror the full `.claude/` Mycelium layout to `<project_root>/mycelium-state/` (identical structure: canvas/, diamonds/, memory/, harness/, evals/, jit-tooling/). Mirroring is a logged HARD GATE mitigation, never silent: every PASS claim against mirrored artifacts carries the caveat. Do not attempt to evade the permission matcher (wrapper scripts, path tricks) — the control is the operator's, and the run respects it.
4. **Re-integration.** The mirror is non-canonical. The next interactive session reviews `mycelium-state/`, moves adopted state into `.claude/` (Read-before-Write rules apply), and logs the adoption in the decision log. Until then, canvas state under `.claude/` is authoritative and the mirror is a pending proposal.
5. **Path hygiene.** Use literal absolute paths in Bash; do not rely on `$CLAUDE_PROJECT_DIR` expanding in headless mode.

## Per-skill behavior (from the 2026-06-11 desk audit of all 54 skills)

| Skill / interaction point | Autonomous behavior |
|---|---|
| setup — AGENTS.md consent | rung (a): documented auto-mode default |
| interview — Phase 6 `runtime_llm` question | rung (a): documented default false |
| metrics-pull — missing config | rung (a): auto-routes to metrics-detect (config confirmation itself stays human-only) |
| xai-check — user_facing_decisions unknown | rung (a): defaults to tier `limited` with note |
| log-evidence — no matching task | rung (a, partial): surfaces gap, offers paths |
| interview — brief Q1–Q4, depth menus | rung (b): persona answers, internal_simulated |
| assumption-test — Step 5 prediction | rung (b) + pre-commit ordering rule (prediction ledgered before running anything) |
| diamond-assess — cognitive forcing, coaching check | rung (b): see inline marker in the skill |
| diamond-progress — cognitive forcing | rung (b): see inline marker in the skill |
| diamond-progress — approval, kill | registry rules: see inline markers in the skill |
| mocked-persona-interview — spectrum + stop-condition pre-commits | rung (b) + pre-commit ordering rule: see inline marker in the skill |
| migrate-from-legacy, eval-runner retirement, delivery-bootstrap installs, metrics config | human-only registry: rung (c) |
| 31 of 54 skills (render fleet, jtbd-map, ost-builder, cynefin-classify, reflexion, security/privacy/a11y checks, …) | no blocking points; fully autonomous-capable as-is |

## What a successful autonomous run looks like

All reachable artifacts written (canonical paths or caveated mirror), every substitution ledgered with the right rung, every simulated artifact tagged, evidence gates failed honestly where evidence is simulated-only, human-only gates left untouched with rung-(c) entries, self-audit complete. The run hands the human a project that is honest about what a machine could and could not legitimately decide — that handover quality, not gate-crossing distance, is the success metric.
