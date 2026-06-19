---
id: 2026-06-19-cowork-runtime-gap
date: 2026-06-19
contributor: Håvard Bartnes (founder self-dogfood)
contributor_link: CONTRIBUTORS.md
project: Mycelium-test / Mycelium-test2 (Claude Cowork)
mechanism_or_status: partial-fix-shipped (v0.49.21) + platform-gap-documented
commits: ["9f6ca9d"]
subclass: self-dogfood / cross-runtime
---

# cowork-runtime-gap — Mycelium in Claude Cowork: skills port, hook enforcement does not

**Audience**: evaluators weighing whether Mycelium works outside Claude Code; contributors interested in a cross-runtime dogfood with an honest negative result.
**Time to read**: 4 min.
**Last updated**: 2026-06-19.

## The session

On 2026-06-19, ahead of submitting Mycelium to the Claude community plugin directory (which serves both Claude Code and Cowork), the founder installed Mycelium in Claude Cowork and ran it end-to-end to check whether it works there as well as it does in Claude Code.

## What surfaced — wins (the skills port with fidelity)

- `/mycelium:start` composed cleanly: setup, then the 4-question brief, then the four-file write contract (`purpose.yml`, `jobs-to-be-done.yml`, `diamonds/active.yml`, `decision-log.md`).
- `/mycelium:diamond-assess` held L0 correctly: evidence gate FAILED (all internal_stakeholder, zero external_human), confidence 0.15 well below threshold, no progression. Its cognitive-forcing step corrected a human pre-judgment ("nothing is properly registered") against the actual state (4/4 brief artifacts intact; the divergence was the hook layer).
- `/mycelium:assumption-test` produced an operational smoke/fake-door design: riskiest assumption prioritised top-left, Lean-UX 4-part hypothesis, prediction-before-run left blank per Toyota Kata.

The discipline ports, not just the mechanics. The gates that matter to a user are skill-internal, and they ran with their theory intact.

## What surfaced — the gap (one root cause, two symptoms)

Cowork runs the agent in a local sandbox (a container/VM on the user's own machine, "local agent mode"). Captured environment: `pwd` is `/sessions/<session-name>`, `CLAUDE_PROJECT_DIR` is empty, and the project's `.claude/` is bind-mounted at `/mnt/<project>/` with no environment variable pointing to it.

- **F1**: the preflight hook resolves the project root from `CLAUDE_PROJECT_DIR` (or `$PWD`), finds neither, and reports "Memory not yet initialized" on every turn even after setup wrote the files.
- **F3**: the Write/Edit tool refuses paths under `.claude/` ("resolves to a path outside the connected folder" — the bind-mount boundary), so canvas writes route through `bash`, and the read-before-write guard never intercepts them.

Both are the same root cause: Cowork's execution context is not the project root, and the project root is not exposed to hooks.

## The fix, and the honest boundary

- F1 was root-caused from the hook source, not guessed: `PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"` with the variable unset. **v0.49.21** shipped a fix: when the variable is unset, walk up from `$PWD` to find `.claude/`; when it is set, trust it verbatim, so CLI behaviour is unchanged. Testing the fix against the real Cowork project then exposed a second, latent bug (`grep -c '^### ' … || echo 0` printed `0\n0` on a zero-entry corrections file), fixed in the same patch.
- v0.49.21 was confirmed to **run** in Cowork (verified against the materialised plugin snapshot on disk) but confirmed **not to fix F1**: the sandbox `pwd` is not under the project, so walk-up cannot reach the mount. Per the framework's own G-V13 ("no works-claim without runtime proof"), the release was framed as a hardening with Cowork confirmation pending, and then marked not-fixed once the sandbox topology was captured.
- **Verdict**: F1 and F3 are a Cowork-platform gap. The real fix is Cowork exposing the project root to hooks (set `CLAUDE_PROJECT_DIR` to the mount, run hooks from it, or pass it in hook stdin). A Mycelium-side `/mnt/*/` scan was considered and rejected as fragile. v0.49.21 stays as a legitimate improvement for other runtimes that leave the variable unset but do run from the project directory.

## What this case taught the framework

- The skills-versus-hooks split is the load-bearing portability boundary across runtimes. Skill-internal gates travel anywhere skills run; ambient hook enforcement depends on the runtime exposing project context. Mycelium reaches Cowork users as discipline-when-invoked, not discipline-enforced — and the install copy should say so plainly.
- A meta-honesty note worth keeping. Mid-investigation, the operator's own agent misread the absence of `.claude/state/` as "the hooks did not fire" — but `.claude/state/` is Claude-Code-runtime-owned, a fact this very receipts directory had already recorded (see B5 in [plugin-form-dogfood](2026-05-09-plugin-form-dogfood.md)). The misread was caught and corrected in the same session and logged as a consistency-as-evidence cluster instance. The verify-before-conclude discipline the framework sells applied to the person building it.
