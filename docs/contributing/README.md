# Contributing to Mycelium

**Audience**: would-be contributors (issue-openers, PR-authors, friction-finders).
**Time to read**: 5 min.
**Last updated**: 2026-05-08.

The voice authority for any docs change is [contributing/style.md](style.md). Read that before touching `docs/` or README/AGENTS/CONTRIBUTORS.

## The asymmetric ask

Friction-finders get named credit ([CONTRIBUTORS.md](../../CONTRIBUTORS.md) + [docs/receipts/](../receipts/README.md) cross-link). Maintainers retain veto on merging.

The deal is deliberate:

- **Low cost to find friction** — surface it in an issue, a DM, a 30-min call. No PR required.
- **Uncapped credit if it shapes the framework** — your name lands on CONTRIBUTORS.md and a per-cycle case file in `docs/receipts/cases/`. The friction-to-mechanism trace is portable proof; point at it on a CV, on a portfolio, in a conversation.

The framework's bias is to credit the named person who shaped a mechanism, not the maintainer who merged it.

## Two paths

### 1. Open an issue

Highest signal-per-effort if the issue is well-shaped. Good issues:

- Name a specific friction (a moment where the framework felt wrong, a decision it pushed you toward, a gate that fired when it should not have)
- Cite the artifact (commit hash, version, skill name, canvas file)
- Describe the impact (what you lost, what you would have wanted, what you tried instead)
- Suggest a direction if you have one (not required)

The framework's bias is removal over addition; new mechanisms must show their friction. An issue that says "you should add X" without a friction trace will probably get pushback.

### 2. Open a PR

For fixes, mechanical improvements, and new artifacts that fit the existing surface. Good PRs:

- Target a single concern (one corrections.md entry, one validator check, one stub fill)
- Pass `bash .claude/tests/validate-template.sh` and `python3 .claude/scripts/validate_canvas.py` locally
- Update CLAUDE.md version line if the change is "material" per `engine/version-discipline.md`
- Include a corrections.md entry if the PR was triggered by an agent mistake (see `.claude/memory/corrections.md` for shape)
- Match voice per [style.md](style.md)

## What gets credited

**Friction-to-mechanism trace.** Surface a real friction; if it shapes the framework — meaning it lands as a mechanism, an anti-pattern, a guardrail, a corrections.md entry, a validator check, or a docs case file — your name lands on CONTRIBUTORS.md and a `docs/receipts/cases/` entry.

The case file is the receipt the receipt argument rests on. Frontmatter cross-links your CONTRIBUTORS.md anchor; the case body names you in prose where appropriate.

## What gets refused

- **Feature additions without a real use case.** The framework's bias is removal over addition. Show the friction.
- **Style-bikeshed PRs that change voice without functional value.** Voice changes require a corrections.md entry that triggered them.
- **PRs that bypass the framework-guard or framework-discipline.** Use the escape hatch (with debt entry) only for emergencies.
- **Sycophantic prose.** Per L5 sycophancy correction (corrections.md 2026-04-20), evaluation surfaces are anti-promotional. PRs that add marketing voice get rolled back.

## Voice and style

[contributing/style.md](style.md) is authoritative. Tl;dr:

- No "we" / "our" / "us"
- No marketing adjectives
- Hedged confidence; cite evidence
- Information scent on every link
- Audience marker on every doc

## Validation hooks

```bash
bash .claude/tests/validate-template.sh   # structural integrity (24 checks)
python3 .claude/scripts/validate_canvas.py  # canvas YAML schema validation
```

Both must pass before a PR is merge-ready.

### Wiring canvas validation into your own pre-push pipeline

`validate_canvas.py` is invocable as a CLI. Wire it into whatever hook tooling you already use — husky, lefthook, the Python `pre-commit` framework, plain bash, GitHub Actions — by calling:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/scripts/validate_canvas.py"
```

It exits non-zero on schema violation or duplicate-ID detection. The validator auto-detects your `.claude/canvas/` directory; no arguments needed.

A reference git pre-push hook script ships at `$CLAUDE_PLUGIN_ROOT/scripts/git-pre-push-example.sh` for projects that don't already have hook tooling. **Mycelium does not install it for you** — `.git/hooks/` is per-clone state outside the plugin's official surface, and most projects will want their canvas validation called from their existing hook pipeline alongside other checks. To opt in manually:

```bash
cp "$CLAUDE_PLUGIN_ROOT/scripts/git-pre-push-example.sh" .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

Emergency bypass: `git push --no-verify`. Document any use — the hook exists because shipping a duplicate-ID or schema-violation to `origin/main` blocks downstream consumers and leaves the broken commit publicly visible until a follow-up fix lands.

## Where to start

Three concrete entry points:

1. **Read [CONTRIBUTORS.md "How to get listed"](../../CONTRIBUTORS.md#how-to-get-listed)** — the recruitment-shaped framing.
2. **Pick a [Phase 2 stub](../README.md#contents)** — one of the forthcoming docs is good first contribution territory if you can write to the [style.md](style.md) discipline.
3. **Open a "first friction" issue** — even a low-stakes friction is a useful starting signal. The framework needs the data more than it needs polish.

## See also

- [CONTRIBUTORS.md](../../CONTRIBUTORS.md) — who is currently credited
- [docs/receipts/](../receipts/README.md) — per-cycle case files of past contributions
- [contributing/style.md](style.md) — operating voice guide
