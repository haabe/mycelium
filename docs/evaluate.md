# Evaluate Mycelium for your team in ~1 hour

**Audience**: evaluators (lead engineer, PM, founder) deciding whether to adopt Mycelium for a project or team.
**Time to read**: 5 min, or 1h to actually do the evaluation.
**Last updated**: 2026-10-03.

This page is anti-promotional by design. The cost of a bad fit is high (a quarter of frustration with ceremony that does not match your work); the cost of saying so up front is low.

## The honest tradeoff

Mycelium imposes structure before the agent is allowed to start coding. That structure is theory-grounded discipline — 30+ frameworks, theory gates that block progression on insufficient evidence, a canvas of YAML files that tracks every assumption. The structure costs you something:

- **Upfront opinionation tax.** `/mycelium:start` runs a universal brief before the first useful output. Depth and time-cost are chosen *after* the brief, once you have the data to choose. But the brief itself is still time spent before you see value.
- **Vocabulary cost.** Diamond, scale, leaf, gate, OST, JTBD — a learning curve before fluency. The [glossary](glossary.md) compresses it; the curve is real.
- **Conformance cost.** The framework is opinionated about format (canvas YAML schema, decision-log structure, correction shape). If your team has its own discovery vocabulary, there is friction at the seams.

What you get for the tax:

- **It stops a build before code.** Two of three Mycelium dogfood projects shipped; one was stopped in L0 on six simulated users, before any real user was asked. The kill produced 10 framework features. See [macos-fileviewer case](receipts/cases/2026-04-macos-fileviewer.md).
- **Onboarding cost on inherited projects drops.** The canvas IS the spec. A new team member reads the canvas, runs `/mycelium:diamond-assess`, and has product context without a meeting.
- **Decision audit improves.** Every theory gate names its source, and the agent is told to cite it when it records a decision. The decision log asks for the alternatives you rejected and why (`why_not_alternatives`), so a future reader can see which paths were turned down. Both are instructions the agent follows, not checks a script runs.
- **Agent drift gets caught.** The reflexion loop, the pre-task protocol, the gates — these catch the agent jumping ahead. The discipline is mostly invisible until the moment the agent would have committed to the wrong scope.

The framework is most valuable when **deciding what to build is the hard part**. If your decision is settled and you only need execution velocity, this is the wrong tool.

## Who Mycelium is for

See [where Mycelium comes in](../README.md#where-mycelium-comes-in). Tl;dr: solo developers and small teams using AI agents on real products where the wrong-build cost is non-trivial.

## Who Mycelium is NOT for

See [when to use something else](../README.md#when-to-use-something-else). Tl;dr: triage-lane work, pure execution, projects with no real wrong-build risk. Listen to the ceremony-feels-heavier-than-value signal. It is a fit signal.

## What to check in 1 hour

A focused hour beats a half-engaged afternoon. Five 10-minute slices, in order:

### 1. Read the receipts (10 min)

Open [docs/receipts/](receipts/README.md). Read three case files: [macos-fileviewer](receipts/cases/2026-04-macos-fileviewer.md), [drew-hoskins-takehome](receipts/cases/2026-04-30-drew-hoskins-takehome.md), [framework-self-correction](receipts/cases/2026-05-01-framework-self-correction.md). The case files are the framework's evidence — if the receipts do not match the kind of friction your team hits, the framework probably is not for you.

Look for: are the corrections concrete (named commits, named bugs, named people) or vague? If concrete, the framework's claim that "Mycelium gets smarter with each cycle" stands on something. If vague, push back.

### 2. Run a small `/mycelium:start` (15 min)

Install the plugin (`/plugin marketplace add haabe/mycelium`, then `/plugin install mycelium@haabe-mycelium`). It adds a `.claude/` folder and offers an `AGENTS.md` at the root (in non-interactive mode it writes one by default), and touches nothing else, so a real repo is safe. Pick a real project you've been chewing on (a side project, a decision you're about to make at work, a thing you almost started). Run `/mycelium:start` and let the brief run. Watch what the agent does. To see a stop, ask it to create a source file before you answer the brief. It should refuse and offer the questions first. To take it all out again, see [uninstall](uninstall.md).

Look for: does the agent ask questions that surface things you had not considered? Or does it feel like form-filling? The first is the framework working. The second is the framework over-fitting.

### 3. Read [philosophy.md](philosophy.md) (6 min)

The why-opinionated rationale. If you disagree with the load-bearing claims (in-loop preventive > post-run evaluative; theory-grounded > ad-hoc; dogfood is required), the rest of the framework will feel like ceremony. If you nod along, the rest will feel like infrastructure.

### 4. Read 2–3 SKILL.md files for the gates that would fire on your work (10 min)

Pick the two or three skills from [docs/skills/](skills/README.md) that match the gates relevant to your kind of work. If you build customer-facing products: `/threat-model`, `/privacy-check`, `/a11y-check`. If you build AI-containing products: add `/xai-check`, `/regulatory-review`. If you ship to enterprise: add `/dora-check`.

Look for: do the SKILL.md files give you a recipe you would actually run, or marketing prose? Mycelium's bias is recipes.

### 5. Read what the brief wrote (15 min)

Open the first entry in `.claude/harness/decision-log.md` and `.claude/canvas/purpose.yml`, which step 2 left in your repo. Read them as a spec of your own idea. A new project starts at low confidence, and the record says why.

Look for: does the canvas pattern survive your team's evidence discipline? If your team's evidence is mostly post-hoc rationalization, Mycelium's evidence-grounding will rub. If your team values "show me the source", this pattern fits.

## What "good fit" looks like

Concrete signals:

- Your team has been burned by building the wrong thing recently
- You have a junior or new-team member who needs onboarding leverage
- You build at the intersection of design / engineering / product (the canvas is shared documentation)
- You ship products with regulatory or trust surface (security, privacy, accessibility, AI Act exposure)
- You want decision audit to survive personnel turnover

## What "bad fit" looks like

Concrete signals:

- Your work is execution-heavy with bounded scope (build the API endpoint, fix the bug, ship the feature)
- Your team already has strong discovery discipline and you would replace one vocabulary with another
- Your runway is short and you cannot afford an upfront opinionation tax
- You operate in a domain where Mycelium's theory choices do not match your domain (research-heavy science, regulated drug development, etc.)
- Your coding agent cannot run hooks, or you will not trust them. Mycelium runs on Claude Code, Codex, Cursor and opencode (see [install paths](install-paths.md)); without hooks you keep the method and lose the stops

## Next step

If after the 1h evaluation you want to try it on a real project: see [get started](get-started.md). Run `/mycelium:start`, and keep going until your first diamond reaches `close`. How long that takes depends on its scale. Most of the value is in the first complete loop. Abandoning halfway through is a worse signal than abandoning at the start.

If after the evaluation you want to push back: open an issue on the Mycelium repo. Pushback that lands a friction surfaces a corrections.md entry; you get named credit per [CONTRIBUTORS.md "How to get listed"](../CONTRIBUTORS.md#how-to-get-listed).
