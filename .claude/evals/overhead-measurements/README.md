# Mycelium Session Overhead Measurements

Records the actual context token cost of loading Mycelium into a Claude Code session. Addresses the v0.8.2 audit prompted by the BDSK comparison (Daniel Bentes feedback) which claimed "~6k token/session overhead" — a figure that needed verification.

## Methodology

Two ways to measure:

### Method A — Static estimate (cheap, approximate)

Count characters in the files that are **always loaded** at session start:
1. `CLAUDE.md` — full root Mycelium instructions
2. SKILL.md frontmatter for each skill (`name:` + `description:` only, per official Claude Code skills docs: *"skill descriptions are loaded into context, but full skill content only loads when invoked"*)
3. `.claude/settings.json` — parsed but not tokenized
4. Hook registrations — metadata only, not content

**Convert chars to tokens**: rough estimate is ~4 chars per token for English text. For YAML/code, closer to ~3 chars per token.

### Method B — Actual `/context` command (authoritative)

In a fresh Claude Code session with Mycelium loaded:
1. Run `/context` slash command
2. Record total token count
3. Subtract a baseline session without Mycelium (clean repo, no `.claude/` directory)
4. The delta is the real overhead

Method B is authoritative; Method A is useful for trending and CI checks.

## Current Measurement — v0.8.2 (2026-04-09)

### Method A (Static Estimate)

| Component | Size (chars) | Tokens (~4 char/tok) |
|---|---|---|
| CLAUDE.md | 16,724 | ~4,200 |
| 35 × SKILL.md frontmatter (name + description) | ~5,500 | ~1,400 |
| **Total static overhead** | **~22,200** | **~5,600** |

### Verification (BDSK's "6k tokens" claim)

**Partially accurate.** BDSK's critique claimed "~6k token/session overhead." Static estimate gives ~5,600 tokens — close enough that the claim is substantively correct, within rounding.

**But two caveats**:
1. This is the **ceiling**. Skill descriptions are only loaded if Claude Code actually injects them all (research: descriptions are subject to `SLASH_COMMAND_TOOL_CHAR_BUDGET` cap of ~8000 chars, so some may be truncated)
2. The real **per-session** cost depends on whether the user invokes any skills (full SKILL.md content loads on invocation)

### Method B (Actual `/context`)

**Not yet measured.** Running `/context` on a live Mycelium session requires manual intervention and cannot be automated by the agent in this codebase. Scheduled as a manual verification step before the v0.9.0 release.

## Future Measurements

One measurement per minor release. Trend over time. If overhead grows past 10k tokens, consider:
- Skill reduction audit (already planned for v0.10)
- Moving lower-priority content out of the always-loaded CLAUDE.md
- Hierarchical skill loading (meta-skills route to sub-toolkits)

## Log

| Date | Version | Method A (static) | Method B (actual) | Notes |
|---|---|---|---|---|
| 2026-04-09 | v0.8.2 | ~5,600 tokens | not yet measured | Confirms BDSK's "~6k" claim as approximately accurate |
