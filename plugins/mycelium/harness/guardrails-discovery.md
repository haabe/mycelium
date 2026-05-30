# Mycelium Guardrails — Discovery Phase

Loaded when operating within discovery domains (L0-L2 Discover/Define phases). Supplements guardrails-core.md.

## Discovery

**G-D1: Never skip discovery for Complex-domain problems** `REVIEW` `scope`
Complex problems (Cynefin) require probe-sense-respond. Applying best practices or expert analysis to Complex problems will produce wrong answers with false confidence.
*Source: Snowden (Cynefin), Smart (BVSSH)*

**G-D2: Never treat a single interview as sufficient evidence** `NUDGE` `quality`
Require triangulation: at least 2 independent evidence types. Single-source evidence is anecdotal (0.3 on Gilad's confidence meter), regardless of how compelling it feels.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D3: Never ask hypothetical or leading questions in research** `NUDGE` `quality`
Use story-based interviewing: ask about specific past behavior ("Tell me about the last time you..."), never hypothetical preferences ("Would you use X?").
*Source: Torres (CDH), Kahneman (Thinking Fast and Slow)*

**G-D4: Never validate opportunities using only one evidence type** `NUDGE` `quality`
Each opportunity in the OST must have evidence from at least 2 sources. Frequency data alone is insufficient.
*Source: Torres (CDH), Gilad (Evidence Guided)*

**G-D5: Always run bias checklist before conducting research** `NUDGE` `quality`
Review `.claude/harness/cognitive-biases.md` before designing interviews, surveys, or experiments.
*Source: Shotton (Choice Factory), Kahneman (Thinking Fast and Slow)*

**G-D6: Always map emotional and social dimensions, not just functional** `NUDGE` `quality`
User needs have three dimensions: functional, emotional, social. Mapping only functional needs misses the actual hiring criteria.
*Source: Christensen (Jobs to be Done)*

**G-D7: Always route an in-flight idea into the OST and state where it landed, its disposition, and its scale** `NUDGE` `scope`
When the user surfaces a feature or idea mid-build, route it into the existing OST *in the same turn* — a new entry in `canvas/opportunities.yml` (with `scale`+`parent` set), a GIST solution leaf in `canvas/gist.yml`, or an archive-with-reason in `canvas/archived-solutions.yml`. Do not absorb it into chat to be "added later": an idea that lives only in the conversation is lost on the next session (the user's own "lost in the noise" fear), and a growing un-routed list is the backlog anti-pattern — accumulation decoupled from the active loop. After routing, state three things visibly: **where** it landed (file + id), **its disposition** (build-now / scoped-child-opportunity / archived-with-reason), and **its scale** relative to the active diamond (is this part of the current diamond, or its own thing further down the L0–L2 axis — read straight off the `scale`+`parent` fields). When you *challenge* a proposed idea, the challenge still resolves to one of those dispositions — never leave the outcome invisible. Fire this proactively on idea accumulation, not reactively after the user pushes back.
*Source: Torres (CDH/OST), leaf-lifecycle Discard/Archive Protocol; graduated from Alex cohort signals 3/4/5/6 (`docs/receipts/cases/2026-05-30-alex-cohort-sessions-2-3.md`)*

## Strategic (discovery-adjacent)

**G-P2: Never ignore BVSSH dimensions** `NUDGE` `quality`
When evaluating progress, check ALL five dimensions. Do not sacrifice Safer or Happier for Sooner.
*Source: Smart (BVSSH)*

**G-P6: Always play devil's advocate before major transitions** `NUDGE` `quality`
Before progressing a diamond to a new scale, systematically challenge current assumptions.
*Source: Kahneman (Thinking Fast and Slow), Shotton (Choice Factory)*
