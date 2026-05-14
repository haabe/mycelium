---
name: wardley-map
description: "Create or update a Wardley Map of the value chain. Maps user needs, components, evolution stages, and strategic gameplay."
instruction_budget: 10
---

# Wardley Mapping

Visualize your value chain and make strategic decisions. Source: Simon Wardley.

## Preflight: Read target canvas file(s) before any Write/Edit

**Hard rule.** Before issuing `Write` or `Edit` against any `.claude/canvas/*.yml`, use the **Read tool** on that file in this session. Claude Code's Read-before-Write check requires the `Read` tool specifically — `cat`/`head`/`grep` via Bash do NOT satisfy it.

**Edit vs Write — different cost profiles** (verified 2026-05-14):
- **`Edit`** (exact-string replacement): `Read` with `limit: 1` satisfies the check at ~50 tokens. State-tracking is per-file, not per-byte — subsequent `Edit` calls work anywhere in the file. Use this for partial updates against large canvas files (e.g., `purpose.yml` at 800+ lines).
- **`Write`** (full replacement): do a **full Read** first. Write obliterates the file; you should see what you're about to replace. The `limit:1` shortcut is *not* appropriate here.

Original failure mode: anti-pattern #7 instance #5, 2026-05-09 — agent conflated Bash `head` with the Read tool, lost ~14k tokens to a Write-fail → remedial-full-Read → re-Write loop. The `limit:1` discipline (graduated 2026-05-14, v0.23.18) prevents the second-order cost where the agent *correctly* follows the rule but full-Reads every time.

If this skill writes to multiple canvas files, register each one first (limit:1 for Edit-only paths; full Read for Write paths).

See `CLAUDE.md` *Canvas writes — Read before Write* for the canonical rule.

## Mapping Process

### 1. Identify the User
Who is the map for? What scope?

### 2. Identify User Needs
What does the user need? Place at the top of the map (most visible).

### 3. Map the Value Chain
What components are needed to serve those needs? Draw dependency lines top-down.

### 4. Assess Evolution Stage
For each component:
| Stage | Characteristics | Strategy |
|-------|----------------|----------|
| **Genesis** | Novel, uncertain, high failure rate | Explore, experiment, small teams |
| **Custom** | Better understood, bespoke builds | Build or partner, reduce uncertainty |
| **Product** | Standardized, feature competition | Buy or build competitively |
| **Commodity** | Utility, cost competition | Consume as service, don't differentiate here |

### 5. Add Movement
Mark components that are evolving (arrow pointing right). All components evolve over time.

### 6. Identify Patterns
- Components in Genesis = Complex domain (Cynefin) -> probe
- Components in Commodity = Clear domain -> best practice
- Evolution mismatch = waste (building custom what you should buy as commodity)

### 7. Apply Gameplay
Strategic options based on the map:
- Open source: Accelerate commoditization
- ILC: Innovate -> Leverage -> Commoditize
- Ecosystem: Build platform, commoditize lower layers
- Tower and moat: Invest in defensibility

## Output
Update .claude/canvas/landscape.yml with components, evolution stages, movements, and gameplay options.

## Decision Log (MANDATORY per G-P4)
**APPEND** a `### Wardley Map Assessment` entry to `.claude/harness/decision-log.md` with: components mapped, evolution stages, strategic gameplay identified, recommendations.

## Connection to Other Frameworks
- Evolution stage maps to Cynefin domain (use `/mycelium:cynefin-classify`)
- User needs at top map to OST outcomes (use `/mycelium:ost-builder`)
- Strategic gameplay informs GIST goals (use `/mycelium:gist-plan`)
