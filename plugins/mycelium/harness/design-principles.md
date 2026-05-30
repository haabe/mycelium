# Design Principles — How Mycelium Relates to Its Human

`engineering-principles.md` governs how the agent writes *code*. This file governs how the framework treats the *person* using it.

Mycelium is a discipline imposed on an agent on behalf of a human. A discipline that disrespects the human's autonomy gets one of three responses — abandonment, gaming, or resentment — none of which produce better products. The guardrails earn their keep only if the person on the other side stays a willing, capable collaborator. These principles keep that true.

The behavioral payload: when you make a UX call — surfacing a skill, proposing tooling, wording a gate, designing any new framework affordance — these are the constraints. They are *why* the framework nudges rather than pushes, and the standard a new affordance must clear.

## Self-Determination Theory is the backbone (Deci & Ryan)

People have three basic psychological needs. A framework that starves them gets compliance-or-abandonment; one that feeds them gets durable, self-sustaining engagement. The rest of this file is these three needs made concrete.

**Autonomy — menu, not mandate.** The human stays the decider; the framework informs and offers.
- JIT tooling *offers* a menu and asks "want help configuring?" — it never auto-installs or prescribes a ruleset (`${CLAUDE_PLUGIN_ROOT}/jit-tooling/detector.md`).
- Skills are *suggested* at transitions with their trigger cited, not forced.
- The escape hatch always exists: a capable professional can bypass the process for cause, documented and paid back (`${CLAUDE_PLUGIN_ROOT}/orchestration/escape-hatch.md`).
- A gate states what evidence it needs and why; it does not seize the wheel.

**Competence — make the human more capable, and show your work.** The framework must leave the user *more* able, not dependent.
- Surface the *why*: citations, gate rationale, and plain-language status translations (`${CLAUDE_PLUGIN_ROOT}/engine/status-translations.md`) exist so the user builds a mental model, not a habit of deferring.
- "The agent earns the right to code" is a **competence bar cleared**, never a toll paid. The reward of a gate is the soundness of the decision behind it.
- Watch the inverse: the Cognitive Offloading Loop (`anti-patterns.md`) is what competence-erosion looks like — prompts going abstract, the human delegating *judgment*. Feeding competence is the antidote.

**Relatedness — knowledge is co-owned, not locked in the agent's context.**
- The canvas is a shared artifact, committed to git, readable by any teammate starting cold. That is a *relational* design choice, not just a storage one.
- See "Psychological ownership & collective efficacy" below for the mechanism.

## Pink's Drive — the communicable surface (Autonomy, Mastery, Purpose)

Pink's *Drive* (2009) is the memorable popularization of SDT (plus Herzberg). Use **Autonomy / Mastery / Purpose** when *explaining* the framework's stance to a user — it lands faster than "competence-need satisfaction". The mapping: Autonomy = autonomy; Mastery = competence over time; Purpose maps directly onto L0 (Sinek's Golden Circle — *why we exist*). It is the same theory wearing accessible words; don't treat it as a separate gate.

## Herzberg's Two-Factor Theory — triage lens for framework defects

Herzberg splits what shapes satisfaction into two non-symmetric classes:

- **Hygiene factors** — their *absence* demotivates; their presence merely fails to annoy. For Mycelium: a fast validator, quiet output, no false positives, clean error messages, low friction. A false-positive check is a hygiene *defect* — it doesn't make the framework better, it makes it *painful*, and pain drives abandonment. (Check 12's phantom-15 over-count, fixed v0.34.1, was exactly this.)
- **Motivators** — their presence *creates* satisfaction: the competence of a hard-won decision, visible growth, purpose.

The triage rule: **fix hygiene defects to stop demotivating; invest in motivators to create satisfaction — and don't confuse the two.** Polishing a motivator while the validator cries wolf is misallocated effort; the hygiene defect will sink engagement regardless.

## Psychological ownership & collective efficacy — why canvas-as-code matters

- **Psychological ownership** (Pierce, Kostova & Dirks, 2001): people steward, defend, and invest in what feels like *theirs*. Control, intimate knowledge, and self-investment are what create the feeling.
- **Collective efficacy** (Bandura, 1997): a group's *shared belief* in its joint capability raises what the group is willing to attempt and how long it persists.

The canvas committed to git is the mechanism for both. It converts the agent's private, evaporating context into a shared, owned, inspectable artifact — something a team can point at, correct, and feel collectively responsible for. This is the design reason "the canvas is the source of truth," not merely a convenience.

## Theory Y, not Theory X (McGregor) — the meta-stance

McGregor's two managerial assumptions: **Theory X** — people are lazy, avoid responsibility, and must be coerced and controlled; **Theory Y** — people seek responsibility, exercise self-direction, and pursue mastery when conditions allow.

Mycelium's guardrails are built on **Theory Y**: they exist to *elevate a capable professional's work*, not to *police a lazy one who can't be trusted*. A gate that blocks is scaffolding toward a sounder decision, not a cage. The tension is genuine — a dense, blocking gate set *can read as* Theory-X distrust even when Theory-Y elevation was intended — and is worth periodically auditing (see `${CLAUDE_PLUGIN_ROOT}/harness/theory-tensions.md`). Relatedly, the stance is **transformational, not transactional** (Burns; Bass): the framework leads by raising the work toward purpose, not by trading rewards for compliance — which is also *why* gamifying the discipline backfires (next section).

## The corrosion to avoid

Extrinsic reward crowds out intrinsic motivation — the **overjustification effect**. Never gamify the framework's own discipline loop (points, badges, streaks, XP, leaderboards). It substitutes a token for the craft and collapses the moment the token stops mattering. Full detection rule and the boundary with legitimate *end-user* reward design: `${CLAUDE_PLUGIN_ROOT}/harness/anti-patterns.md` → "Gamified Discipline (Overjustification)".

---

*Sources: Deci & Ryan (Self-Determination Theory, 1985; 2000); Pink (*Drive*, 2009); Herzberg (*The Motivation to Work*, 1959; "One More Time: How Do You Motivate Employees?", HBR 1968); Pierce, Kostova & Dirks (psychological ownership, 2001); Bandura (collective efficacy, *Self-Efficacy*, 1997); McGregor (*The Human Side of Enterprise*, 1960); Burns (*Leadership*, 1978) & Bass (transformational leadership, 1985); Lepper, Greene & Nisbett (overjustification, 1973); Deci, Koestner & Ryan (extrinsic-reward meta-analysis, 1999).*
