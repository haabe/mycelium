# Wayfinding: "You Are Here" Map

Renders a text-based journey map showing where the user is in the L0→L5 progression.

Source: NNGroup "You Are Here" navigation pattern (https://www.nngroup.com/articles/navigation-you-are-here/).

## Why This Exists

After `/interview` creates the first diamond, users need a mental model of the full journey. Without it, they're oriented to their current task but blind to the structure. The map answers three questions instantly:

1. **Where am I?** (highlighted current position)
2. **What's the full journey?** (all six scales visible)
3. **What does each step mean?** (plain-language descriptions)

## When to Render

| Trigger | Context |
|---------|---------|
| After `/interview` completes | "Here's the journey you just started" |
| At session start (before `/diamond-assess` output) | "Here's where you left off" |
| After `/diamond-progress` records a decision | "Here's where you are now" |
| On user request | Any time — the map is always available |

## How to Render

**STRICT — reproduce the template literally.** Render the template below verbatim; substitute only the dynamic values (symbol per scale, decision markers, confidence text, next-action text). Do not redesign the layout. Do not add box-drawing characters or vertical connectors. Do not change the title text. Do not omit scales. Do not paraphrase the scale descriptions.

Common deviations seen in the wild — all wrong:
- ❌ Title `You Are Here — Wayfinding Map` → use `YOUR JOURNEY` (caps, no subtitle).
- ❌ Symbol `●` → use `◆` (active), `✦` (completed), `○` (not started), `–` (skipped).
- ❌ Vertical tree with `┐ │ ┘` connectors → use one line per scale, its decisions left to right with `→`.
- ❌ Inline confidence on the active line (e.g., `← YOU ARE HERE (target set, confidence 0.3)`) → confidence belongs in the footer, after the closing horizontal rule.
- ❌ Skipping the plain-language description line under each scale → always include it.

Read `diamonds/active.yml` and render the map. Rules:

### Scale indicators

| State | Symbol | Meaning |
|-------|--------|---------|
| Active diamond exists | `◆` | This scale has a diamond in progress |
| Completed | `✦` | This scale's diamond completed |
| Not yet started | `○` | No diamond spawned for this scale yet |
| Skipped | `–` | Not used since v0.247.0: no scale is skipped (every rung needs its parent diamond) |

### Decision indicators (for active/completed diamonds)

Show the loop's four steps on the same line as the scale: `set target → commit to build → release
→ close` (`commit to build` stands for `start_experiment` and `commit_to_build`, recorded together).
They are read from the diamond's `decisions` (DL-1372 V1; since v0.309.2 the map says them, not the
four phases). An L0 is not a loop: its line is `purpose stated ✓` once it records `state_purpose`,
else `purpose not stated yet ←`. Mark each step:

| State | Rendering |
|-------|-----------|
| Recorded | `✓` after the step |
| The next decision | `← next` after the step |
| Still to come | The step only (no marker) |
| No diamond at this scale | `·` placeholder |

A loop that iterates (another `start_experiment` after `commit_to_build`, DL-1373) stays where it
is on the map: the experiment is a step inside it, not a step back.

### Plain-language descriptions

Each scale gets a one-line description from `status-translations.md`:

| Scale | Description |
|-------|-------------|
| L0 Purpose | Why this product exists |
| L1 Strategy | Where to play |
| L2 Opportunity | What problems to solve |
| L3 Solution | How to solve the problem |
| L4 Delivery | Build and ship |
| L5 Market | Get to users |

### Footer

Always include:
- **Confidence** line: current confidence in plain language + what would increase it
- **Next** line: the single most important next action in plain language

### Rendering Template

```
YOUR JOURNEY
─────────────────────────────────────────────────────

L0  Purpose         ◆  purpose not stated yet ←
    Why this product exists

L1  Strategy         ○  · · · ·
    Where to play

L2  Opportunity      ○  · · · ·
    What problems to solve

L3  Solution         ○  · · · ·
    How to solve the problem

L4  Delivery         ○  · · · ·
    Build and ship

L5  Market           ○  · · · ·
    Get to users

─────────────────────────────────────────────────────
Confidence: Moderate (0.45) — based on community signals, no user testing yet
Next: Test purpose framing with real builders
```

### Multiple active diamonds

When the tree has branched (e.g., L0's purpose stated, L1 with its target set, L2 with no decision yet):

```
YOUR JOURNEY
─────────────────────────────────────────────────────

L0  Purpose         ◆  purpose stated ✓
    Why this product exists

L1  Strategy         ◆  set target ✓ → commit to build ← next → release → close
    Where to play

L2  Opportunity      ◆  set target ← next → commit to build → release → close
    What problems to solve

L3  Solution         ○  · · · ·
    How to solve the problem

L4  Delivery         ○  · · · ·
    Build and ship

L5  Market           ○  · · · ·
    Get to users

─────────────────────────────────────────────────────
Active: 2 diamonds (L1 Strategy, L2 Opportunity)
Focus: L1 Strategy — narrowing where to compete
Confidence: L1 0.6, L2 0.3
```

### Skipped scales

None since v0.247.0: every scale opens under the one above it, so no line is ever rendered as
skipped (the `–` symbol above is kept only so an old map can still be read). Until v0.309.4 this
section showed an example skipped L1, which contradicted that rule.

### Post-interview first render

After `/interview`, add an introductory line:

```
Welcome to your product journey. Here's the map:

YOUR JOURNEY
─────────────────────────────────────────────────────
...
```

### Adapting to Drew Hoskins' L3-L5 concern

The map descriptions for L3-L5 should make their distinct purpose visible:

- L3 is "How to solve the problem" — **designing** solutions, comparing options, testing assumptions
- L4 is "Build and ship" — **implementing** the chosen solution with quality gates
- L5 is "Get to users" — **reaching** the audience, positioning, launch

The descriptions are deliberately short but distinct. If a user asks "why is L3 different from L4?", the map answers it: one is designing, the other is building. Theory gates make them behave differently (L3 has Four Risks + ICE; L4 has DORA + OWASP + DoD).

## What NOT to Do

- Don't make the map interactive (it's text output, not a UI)
- Don't show theory gate details in the map (that's `/diamond-assess`'s job)
- Don't show more than 2 lines per scale (keep it scannable)
- Don't omit scales — always show all six, even if not started (the full journey is the point)
