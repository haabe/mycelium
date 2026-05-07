# FAQ

**Audience**: prospective users + evaluators with the questions Mycelium has been asked.
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

The first six questions surfaced at the 2026-05-07 Juniors.dev presentation; the rest are standard OSS.

## From the Juniors.dev presentation (2026-05-07)

### How much does running Mycelium cost in API tokens?

Honest answer: depends on session shape. Mycelium itself adds ~6,000 tokens of harness overhead per session (hooks, gates, pre-task context). The bigger cost is what the framework refuses to skip — `/interview` is 15-30 minutes of structured Q&A that an unharnessed agent would skip. That cost is borne whether it's worth it or not.

External vendor estimate (2026-04): Claude Code averages ~$13/day for an active developer. Mycelium's overhead is well under 10% of that on the projects observed so far. The framework is configuration files, not a service — there is no Mycelium subscription.

If token cost is the binding constraint and discovery is settled, the framework is over-engineered for the work. See [Who it's not for](../README.md#who-its-not-for).

### Will Mycelium's skills clash with my own slash-commands?

No collision in Claude Code's resolution order: user-defined skills take precedence over Mycelium's. If you have `/interview` already, yours runs. Mycelium discovers skills from `.claude/skills/*/SKILL.md` and registers them as candidates; it does not override existing names.

If you want Mycelium's `/interview` AND your own, rename one. The framework has no opinion on which.

### Does Mycelium help when I already know exactly what to build, or only when I'm exploring?

The framework's value concentrates upstream. If your problem statement is settled, your user is named, your scope is bounded, and your only friction is execution velocity — Mycelium adds ceremony with thin marginal value. Use [Addy Osmani's agent-skills](https://github.com/addyosmani/agent-skills) or paddo.dev's [boring agents](https://paddo.dev/blog/boring-agents-ship/) patterns.

If your idea is rough — you're not sure who it's for, or whether it's a real problem, or what "done" looks like — Mycelium's discovery scales (L0–L2) earn their cost. The clearer the idea, the less you need; the rougher the idea, the more you do.

### Will this work with OpenAI Codex / Cursor / Aider / Copilot?

Partially. Mycelium's full enforcement layer (hooks, gates, reflexion loops, framework-guard, secret detection) is Claude-Code-specific today. The portable surface is canvas reading + writing + decision logging — non-Claude-Code agents can read `.claude/canvas/*.yml` and `.claude/memory/corrections.md` to operate on the same evidence base, but gates do not fire automatically.

See [AGENTS.md](../AGENTS.md) for the minimal path on non-Claude agents and concrete operating models per agent class.

### What is dogfooding?

Using a tool on its own development. Mycelium's framework is dogfooded on Mycelium itself — the friction the founder hits while building Mycelium becomes corrections that shape Mycelium.

In Mycelium specifically, the `meta_dogfood` project type formalizes this: when a project's purpose is "improve the framework", canvas writes target the framework's own discovery scales rather than a downstream product's. See [philosophy.md](philosophy.md) for why this is required, not optional.

### When two team members edit the same canvas file, how does Mycelium handle the conflict?

Canvas files are YAML committed to git. Conflicts resolve through git's normal merge — same as code. Mycelium's specific discipline: `_meta` blocks (version, last_validated, evidence_type, structural_level) are the source-of-truth markers; if two branches edit different fields of the same canvas section, the merge is mechanical. If two branches edit the same field, the higher `last_validated` date wins by convention (the more recent evidence supersedes the older).

`/canvas-sync` packages canvas state for cross-session sync; it does not auto-merge — git does that. See [usage-modes.md](usage-modes.md#team-mode) for the team workflow.

## Standard OSS

### What's the license? Can I use it commercially?

MIT License. Commercial use is permitted. Mycelium is not affiliated with any of the cited authors or publishers — citations are educational and credit the intellectual foundations.

### How do I contribute?

See [CONTRIBUTORS.md](../CONTRIBUTORS.md) for who's listed and the "How to get listed" recruitment-shaped section. See [docs/contributing/](contributing/README.md) for process.

The framework's bias is to credit the named person who shaped a mechanism, not the maintainer who merged it. Surface friction; if it shapes the framework, you land in [docs/receipts/](receipts/README.md).

### How do I verify the receipts claims?

Every case file in [docs/receipts/cases/](receipts/) carries YAML frontmatter naming the commit hashes the case produced. Click through to the commits on GitHub. The receipts argument stands on its receipts.

### Is Mycelium itself regulated under the EU AI Act?

No — Mycelium is configuration files plus orchestrated prompts, not an AI system in the Act's definition. Products *built with* Mycelium may be regulated. See [regulatory.md](regulatory.md) for the mapping table and `/regulatory-review` for the per-product check.

Mycelium does not certify compliance. For compliance decisions, consult qualified EU AI law counsel.

### How does Mycelium decide what's a "small project" vs a "complex product"?

`/interview` Phase 0 asks: "How much time do you have?" Under 8h selects inline discovery (skip /interview entirely, weave 3 questions into the first task). 8–48h selects sprint mode. 48h+ selects the full interview. After Phase 0, project complexity is inferred from canvas density and the number of L2 opportunities — more opportunities + more scenarios = more diamond depth.

You can override at any time. The framework recommends; it does not force.
