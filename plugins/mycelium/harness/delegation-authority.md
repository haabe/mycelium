# Delegation Authority

Who decides — agent or human — for each **execution** decision in the lifecycle, and at what level human authority is **absolute** (non-delegable).

Mycelium's guardrail tiers (`guardrails-core.md`) govern the agent's *epistemic* discipline: don't fabricate evidence, read corrections first, cite theory. This file extends the **same three tiers** (BLOCK / REVIEW / NUDGE — no new vocabulary) to *execution* decisions: what the agent may build, deploy, delete, or send on its own versus what a human must own.

It is the repo anchor for behavioral-contract **N9** (*"never take a destructive / hard-to-reverse / shared-state action without confirmation unless pre-authorized"*), which previously had none, and the lifecycle-aware form of the operating harness's "executing actions with care" doctrine.

*Source: Sheridan & Verplank (levels of automation, 1978 — authority is a spectrum, not a binary); human-in / on / out-of-the-loop (AI governance); McGregor Theory Y + overjustification (`design-principles.md` — the layer must reduce friction on safe actions or it self-defeats). Contrast: ADLC's "agents execute, humans govern" (Saar, adlc.io) names the seam but leaves it a binary; this operationalizes it.*

## The rule

Score each execution decision on **consequence**, a function of two inputs:

- **Effective reversibility** — can the action be undone such that prior state *and others' perception* are restored? A deleted Slack message or a posted PR comment is technically removable but **not** effectively reversible (the impression persists; third-party content may be cached). "Reversible" means effective, not `git revert` exists.
- **Aggregate blast radius** — scored at the **campaign / fan-out level**, not per call. One outreach message is low; the agent sending one hundred is a mass action. One row updated is low; a migration across a shared table is not.

Authority follows consequence:

| Consequence | Tier | Authority |
|---|---|---|
| Low (reversible, contained) | `NUDGE` | Agent acts autonomously |
| Mid (social visibility, shared-but-recoverable state) | `REVIEW` | Agent prepares; human approves before the act |
| High (irreversible **and** non-trivial, or high aggregate blast) | `BLOCK`-equiv | **Absolute human** — agent may orchestrate, human accepts the risk |

It is **not** a clean `OR` of two booleans. An irreversible-but-trivial action (deleting a temp file the agent itself created) is low-consequence and stays autonomous — gating it would be exactly the ceremony that gets the layer abandoned. Absolute authority attaches at **high consequence**, where the *combination* of irreversibility and blast radius is severe.

### Absolute regardless of consequence: the no-standing list

Some decisions are non-delegable not because of blast radius but because the agent has **no standing** to make them — their legitimacy comes from human accountability, not correctness. This list is **human-enumerated and fixed**, never a per-instance agent judgment (an agent that self-judges its own standing will rule in its own favor):

1. **What bet to make** — which opportunity/solution to pursue (a value judgment).
2. **Accepting a security / privacy / regulatory / ethics tradeoff** — the agent surfaces options and a recommendation; the human accepts.
3. **Modifying this authority map itself** — maximal blast radius (governs all future agent behavior); self-referentially non-delegable.

## Authority map

| Decision class | Consequence | Tier | Who decides | Agent's role |
|---|---|---|---|---|
| Draft / spec / research / explore | low | `NUDGE` | agent | acts, logs |
| Write code, tests, local edits (reversible) | low | `NUDGE` | agent | acts autonomously |
| Commit to local / feature branch | low | `NUDGE` | agent | acts |
| Merge to shared branch / open PR | mid (social) | `REVIEW` | human approves | prepares, requests |
| Send external message / outreach (esp. at fan-out) | mid→high | `REVIEW`→`BLOCK` | human approves | drafts |
| Choose the bet / what to build | no-standing | `BLOCK`-equiv | human only | proposes, recommends |
| Accept security / privacy / regulatory / ethics tradeoff | no-standing | `BLOCK`-equiv | human only | surfaces options + recommendation |
| Production deploy to real users | high | **risk-envelope** | human sets envelope; agent acts within it | orchestrates canary / flag / rollback |
| Destructive / shared-state op (drop table, force-push, delete branch) | high / irreversible | `BLOCK`-equiv | human only | refuses absent explicit instruction |
| Modify this authority map | max blast | `BLOCK`-equiv | human only | proposes |
| Emergency harm-reduction, no human reachable | high | escape-hatch | agent acts to reduce harm | logs payback |

### Risk envelope (the friction-reducer)

Production deploy uses a **risk envelope**, not per-deploy approval. The human sets thresholds **once** (e.g., canary error-rate ceiling, max auto-rollout %); below them the agent proceeds autonomously, above them it escalates. A one-time threshold-set replaces a recurring gate — this is how the dangerous class earns a wide autonomous lane instead of constant ceremony. (Envelope as a structured canvas field is demand-pulled: add it when a real L4 delivery diamond needs to record one, per the framework's "don't build speculatively" discipline.)

## Two failure directions

- **Under uncertainty, round up.** If the agent cannot tell whether an action is effectively reversible or what its blast radius is, treat it as the **more-governed** tier and escalate. Uncertainty is not a licence to act.
- **Emergencies defer to the escape hatch.** When a high-consequence action is needed to *reduce* harm and no human is reachable (e.g., rolling back a bad prod deploy), the agent may take the safer action under `${CLAUDE_PLUGIN_ROOT}/orchestration/escape-hatch.md`, with a mandatory payback log entry. "Absolute" has a documented override; it is not a deadlock.

## Over-gating self-check (the gate this doctrine must pass)

A delegation layer that pushes the everyday loop into `REVIEW` swamps the human, triggers the overjustification collapse (`design-principles.md`), and gets gamed or abandoned — the Theory-X reading the framework exists to avoid. So the layer's **primary job is to widen the autonomous lane**, marking the reversible majority as agent-OK so the human sees only the genuinely consequential.

**Pass condition:** tally the high-frequency delivery loop — write code, run tests, local commit, draft, research. If any of those land above `NUDGE`, the cut is wrong and must be redone. `REVIEW`/`BLOCK` is the minority, reserved for the rare and consequential.

The opposite failure is **over-delegation**: a human who stops performing the `REVIEW`/`Accept`/`Approve` actions the map expects is sliding into the **Cognitive Offloading Loop** (`anti-patterns.md`). Authority that is nominally human but never exercised is not delegation — it is abdication.
