# Mycelium Guardrails — Core (Always Loaded)

Universal constraints that apply regardless of phase or scale. These are the minimum instruction set for every task.

## Enforcement Levels

- **BLOCK**: Mechanically prevented via hook. Cannot proceed.
- **REVIEW**: Gates diamond progression. Agent must satisfy before `/diamond-progress` advances.
- **NUDGE**: Advised, not blocking. Logged for awareness.

Only BLOCK is computationally deterministic. REVIEW and NUDGE are inferentially enforced (Böckeler).

## Security (universal)

**G-S1: Never store, log, or transmit user secrets in plaintext** `BLOCK` `safety`
Credentials, tokens, API keys, passwords must be encrypted at rest and in transit. Never commit them to version control. Never include them in error messages or logs.
*Source: OWASP Secure by Design*

## Process (universal)

**G-P1: Never progress a diamond without updating the canvas** `REVIEW` `quality`
Every diamond transition must be reflected in the appropriate canvas files. The canvas is the single source of truth -- if it's not in the canvas, it didn't happen.

**G-P4: Always log decisions in the decision log** `REVIEW` `quality`
No significant decision (diamond transition, solution selection, architecture choice, scope change) happens without a logged entry in `.claude/harness/decision-log.md`. **Every skill that assesses, evaluates, checks, or progresses a diamond MUST append an entry before completing.** This includes but is not limited to: `/diamond-assess`, `/diamond-progress`, `/dora-check`, `/bvssh-check`, `/team-shape`, `/service-check`, `/canvas-health`, `/bias-check`, `/privacy-check`, `/security-review`, `/launch-tier`, `/wardley-map`, `/cynefin-classify`, `/retrospective`. If the skill produces a finding, the finding goes in the log.
*Source: Dogfood finding F2 (2026-04-20): 3 of 18 scenarios needed retries because skills skipped the decision log on first pass.*

**G-P5: Always read corrections.md before implementation tasks** `BLOCK` `quality`
Past mistakes are expensive lessons. Reading them costs seconds. Not reading them costs hours.
*Source: Mycelium self-learning, n-trax reflexion pattern*

**G-P3: Always cite which theory informed a decision** `NUDGE` `quality`
Every significant decision in the decision log must reference the specific theory/framework that guided it.

**G-P7: Close the loop after every task batch** `REVIEW` `quality`
After completing any batch of changes, before reporting done: (1) verify cross-repo consistency if changes span repos, (2) log corrections for any mistakes made, (3) log patterns for anything reusable, (4) update corrections.md TL;DR if new entries added. If the user has to ask whether this happened, the guardrail already failed.
*Source: Hoskins Ch4 (friction logging), Argyris (double-loop learning)*

**G-P8: Never gamify the framework's own discipline** `NUDGE` `quality`
Do not add extrinsic rewards (points, badges, streaks, XP, leaderboards, completion dopamine) to gates, skills, canvas updates, or protocol adherence. Extrinsic tokens crowd out the intrinsic motivation of building good products — the overjustification effect — and collapse the moment the token stops mattering. Motivate adherence by removing friction (Herzberg hygiene) and surfacing mastery, not by bolting on tokens. Extrinsic/variable reward is a legitimate lever for *end-user* product design (Hook Model, `/launch-tier`), never for the maintainer's own discipline loop.
*Source: Deci & Ryan (Self-Determination Theory), Lepper/Greene/Nisbett (overjustification, 1973). Detection rule: `${CLAUDE_PLUGIN_ROOT}/harness/anti-patterns.md` "Gamified Discipline". Design rationale: `${CLAUDE_PLUGIN_ROOT}/harness/design-principles.md`.*

## Communication (universal)

**G-C1: Layer output — BLUF first, rationale next, discipline notes last** `NUDGE` `quality`
Every emission with discipline-visibility metadata (citations, attribution labels, why-not-alternatives, recommended next skills, bias warnings, anti-pattern references) should layer in three blocks:

1. **BLUF** (Bottom Line Up Front, 1-2 lines, plain register): the actionable claim — verdict, recommendation, finding, or next step. No inline citations. No attribution labels. No theory name-drops. A reader who stops here has the answer.
2. **Rationale** (scannable middle block): why the claim holds. Short sentences. No attribution metadata inline. Theory references stay in the trailing block.
3. **Discipline notes** (under a `---` rule, prefixed `Discipline notes:` or equivalent): citations, `verified | consistency_only | unverified` labels, why-not-alternatives, recommended next skills, anti-pattern cross-references, bias-cluster references, source attributions. Load-bearing — do NOT remove — but lives below the fold where readers who don't need it can skip without scanning cost.

For checklist skills (`/security-review`, `/a11y-check`, `/definition-of-done`): lead with overall verdict + top-3 findings; full per-category checklist goes under the rule.

For decisions/recommendations: why-not-alternatives collapses to one summary line in the body ("considered N alternatives — see notes below"), expanded in the trailing block.

Convention is a nudge, not a limit: a 3-line emission and a 50-line emission both satisfy it as long as the layering holds. Audience-tier sensitivity encouraged — junior / designer / non-native English reader → plainer register; theory-fluent reader → denser trailing block acceptable.

*Source: Sweller (cognitive load theory) + Cowan 2001 (working memory ≈4 chunks) + Nielsen NN/g (F-pattern scanning) + Minto Pyramid Principle + BLUF (military/business comms) + W3C COGA + WCAG 3.0 cognitive accessibility working draft. Graduated 2026-05-26 from cohort-tester-2 friction log ("brain fried from gigantic walls of text"). The chain "wall-of-text → comprehension failure → cohort attrition" is `consistency_only` at N=1 — convention is research-informed, not research-validated for this surface; a `/mycelium:prompt-optimizer` A/B is the right next step.*
