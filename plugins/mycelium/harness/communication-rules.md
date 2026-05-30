# Communication Rules — Rationale, Provenance & Operational Detail

Canonical detail for the **§ Communication Rules** active rules in `CLAUDE.md`. The
root file keeps each rule's lead sentence and its acceptable-form bullets (the parts
that must be active at all times); this file holds the *why*, the graduation history,
the research basis, and the operational sequences that load on demand. **The active
rules in `CLAUDE.md` win** — if this file and the root ever disagree, the root is the
contract and this file is the bug.

---

## Plain-language-first

Use `engine/status-translations.md` to translate diamond states.
- Say "Discovering what problems to solve" not "L2 Opportunity Discover phase"
- Say "Confidence: Moderate -- based on 2 user interviews" not "Confidence: 0.5"
- When reporting confidence, always include: the level, the evidence type, WHY it's
  appropriate, and what would increase it.

## Cite the trigger `(per: <source>)`

Source can be a corrections.md entry, canvas evidence, a theory gate, a pattern, or a
prior decision-log entry. Example: "Suggesting `/threat-model` (per: L4 deliver gate +
threat-model.yml stale 47 days)." Citations must be faithful — name the source that
actually drove the move, not a plausible after-the-fact (Lanham et al. 2023). Tracked
in eval `2026-05-04-xai-inline-attribution`.

## Name the verification surface

Acceptable forms: `Verified: ran [tool]` (ran the underlying tool), `Cited: [source
path:line OR quote]` (traced to source), `Per [speaker/tool/wrapper]: [claim]`
(attributed, not confirmed), `Unverified` (acknowledges the trust-gap).

Without any of these forms, the inferential link from "claim someone made" to "I will
act on this" is invisible and unverifiable. This is the **trust-without-verification
surface of anti-pattern #7** *Consistency-as-Evidence* — historically sub-class (e)
subagent-output-verification, generalized 2026-05-23 to cover any tool/wrapper/dialog
claim the agent didn't independently verify. Recurrence shape: agent reads "pre-existing
tech debt" in validator wrapper text and propagates without running the underlying lint;
agent agrees with founder claim about a named user's behavior without challenging the
evidence source; agent accepts subagent's claim about a Mycelium file without
grep-verifying.

First propagation surface (subagent-output-verification, 2026-05-11) — generalized
2026-05-23 after the EXE001 instance where the validator's "pre-existing" wrapper text
was propagated without running ruff. Same graduation philosophy as `Gated by:` (Grice
maxim of quantity; Sperber & Wilson relevance theory): make the interpolation visible,
don't try to eliminate it. Convention is grep-detectable post-publish; a propagation
without any verification form fails the check. Candidate Check N+2 mechanism flagged in
corrections.md.

**For X / Twitter URLs specifically**: attempt playwright + nitter.net extraction before
defaulting to `Per user:` summary. The WebFetch surface fails on X (HTTP 402 paywall)
and on most Nitter mirrors; playwright with full-browser rendering succeeds where lighter
fetchers don't (verified 2026-05-24 across 4 thread verifications). Sequence: try
`mcp__playwright__browser_navigate` → `mcp__playwright__browser_evaluate` to extract
`.tweet-content` text; if Nitter returns empty, accept `Per user:` summary or ask for
paste. agent-browser CLI also installed but does not work for Nitter pages (renders
empty body; see roadmap decision-log 2026-05-24 benchmark).

## Name the gate before any deferral/threshold/date recommendation

Applies to all recommendations stating "defer to [date]," "ship at [threshold]," "act
when [N]," "after/before [date]," or "until [N]" — including pushback statements
declining proposed work (e.g., "we shouldn't ship X now because Y"), which are
themselves deferral statements. Acceptable forms:
- Explicit: `Gated by: [event that would unblock] — [interventional|observational]`
  (preferred for new agent output where ambiguity would otherwise hide the causal link)
- Canvas-state: `ON HOLD (pending [X])` — canonical for canvas action flags per
  `engine/canvas-guidance.yml#action_flags`, semantically equivalent
- Natural-prose: "Wait for X before Y," "deferred pending X," "until X lands," "X
  remains the gate" — compliant when the gate event is explicitly named in the sentence

If the gate is evidence-arrival, the date is a forecast not a commitment; say so.
Without ANY of these forms, the implied causal link between the date/threshold and the
unblock event is invisible and unverifiable — the **implicit-causal-link sub-class of
anti-pattern #7** *Consistency-as-Evidence* (graduation philosophy: make the
interpolation visible, don't try to eliminate it — Grice maxim of quantity; Sperber &
Wilson relevance theory).

First trigger instance 2026-05-23 (capacity-vs-evidence-gating conflation in
BVSSH-on-l0-purpose deferral); same-turn recurrence at agent's own scope-pushback surface
(2nd instance same day) confirmed the convention must apply to pushback statements.
Pre-Ship #9 ran without catching either instance because the causal link was implicit,
not explicit. Inventory of pre-existing framework prose 2026-05-23: ~0 hard violations,
~8 soft format-mismatches (gate present, alternate form) — the convention's role is to
close the agent-output surface that lacked any gate-naming convention, NOT to retrofit
existing well-formed canvas-state or natural-prose gate naming. Candidate Check N+1
mechanism flagged in corrections.md; graduation criterion is a 2nd hard-violation
instance post-convention.

## Layer output: BLUF → rationale → discipline notes

Per `G-C1` in `guardrails-core.md`. Every emission carrying discipline-visibility
metadata (citations, `verified | consistency_only | unverified` labels,
why-not-alternatives, recommended next skills, bias warnings, anti-pattern references)
splits into three blocks:

1. **BLUF** (1-2 lines, plain register): the actionable claim — verdict,
   recommendation, finding, or next step. No inline citations, no attribution labels, no
   theory name-drops. A reader who stops here has the answer.
2. **Rationale** (scannable middle block): why the claim holds. No attribution metadata
   inline.
3. **Discipline notes** (under a `---` rule, prefixed `Discipline notes:`): citations,
   attribution labels, why-not-alternatives, recommended next skills, anti-pattern
   cross-references, source attributions. Load-bearing — do NOT remove — but below the
   fold.

For checklist skills (`/mycelium:security-review`, `/mycelium:a11y-check`,
`/mycelium:definition-of-done`): lead with overall verdict + top-3 findings; full
per-category checklist under the rule. For decisions: why-not-alternatives collapses to
one summary line in the body ("considered N alternatives — see notes below"), expanded
in the trailing block. Convention is a nudge, not a limit — 3-line and 50-line emissions
both satisfy it as long as layering holds.

Example pattern: `Recommendation: ship as experiment, with explicit kill criteria. \n\n
Two of three evidence pieces are consistency-only and one is unverified — direction is
plausible but not yet attributed. \n\n --- \n Discipline notes: Evidence — 2
consistency_only, 1 unverified (per AP#7, Technique 4). Why-not-alts — (a) defer = no
evidence; (c) drop = premature.`

Graduated 2026-05-26 from cohort-tester-2 friction log ("brain fried from gigantic walls
of text"). Research basis: Sweller (CLT), Cowan 2001 (working memory ≈4 chunks), Nielsen
NN/g (F-pattern), Minto Pyramid, BLUF (military/business), W3C COGA + WCAG 3.0 cognitive
accessibility. The chain "wall-of-text → comprehension failure → cohort attrition" is
`consistency_only` at N=1 — convention is research-informed, not research-validated for
this surface; `/mycelium:prompt-optimizer` A/B is the right next step.
