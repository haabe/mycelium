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
| After `/diamond-progress` transitions | "Here's where you moved to" |
| On user request | Any time — the map is always available |

## How to Render

Read `diamonds/active.yml` and render the map. Rules:

### Scale indicators

| State | Symbol | Meaning |
|-------|--------|---------|
| Active diamond exists | `◆` | This scale has a diamond in progress |
| Completed | `✦` | This scale's diamond completed |
| Not yet started | `○` | No diamond spawned for this scale yet |
| Skipped | `–` | Skipped (e.g., L1 for solo_hobby) |

### Phase indicators (for active/completed diamonds)

Show all four phases on the same line as the scale. Mark each:

| State | Rendering |
|-------|-----------|
| Completed phase | `✓` after the phase name |
| Current phase | `←` pointer + phase name in context |
| Future phase | Phase name only (dimmed — no marker) |
| Not applicable | `·` placeholder |

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

L0  Purpose         ◆  Discover ✓ → Define ✓ → Develop ← → Deliver
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

When the tree has branched (e.g., L0 complete, L1 in Define, L2 in Discover):

```
YOUR JOURNEY
─────────────────────────────────────────────────────

L0  Purpose         ✦  Discover ✓ → Define ✓ → Develop ✓ → Deliver ✓
    Why this product exists

L1  Strategy         ◆  Discover ✓ → Define ← → Develop → Deliver
    Where to play

L2  Opportunity      ◆  Discover ← → Define → Develop → Deliver
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

```
L1  Strategy         –  (skipped — solo hobby, no portfolio strategy needed)
    Where to play
```

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
