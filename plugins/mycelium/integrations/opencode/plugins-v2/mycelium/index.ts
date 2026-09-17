/**
 * opencode-mycelium — enforcement plugin for opencode 2.x (SKELETON / STARTER)
 *
 * opencode 2.0 (npm `@opencode/cli`, stable 2026-09-11) does not load V1 plugins:
 * "V1 plugin implementations do not run in V2. Moving a file or renaming its config
 * entry is not enough." This is the V2 form of ../../plugin/mycelium.ts, which stays
 * in place for opencode 1.x. Install location: `.opencode/plugins/mycelium/index.ts`
 * (auto-discovered; no config entry needed).
 *
 * Covers:
 *   - session `context`     → preflight injection as a system part
 *                             (CC: UserPromptSubmit/preflight.sh). Fires under
 *                             headless `opencode run`.
 *   - tool `execute.before` → read-before-edit guard (CC: the Edit precondition).
 *   - tool `execute.after`  → reflexion prompt on a failed tool call
 *                             (CC: PostToolUseFailure/reflexion-gate.sh). This is the
 *                             hook V1 never had (opencode #27900): V2 fires
 *                             `execute.after` with `status: "error"`.
 *
 * NOT covered (TODO, same list as the V1 skeleton): Stop/turn-end guardrail,
 * gate/scope/secret-scan, post-write nudge, change-log, read-log.
 *
 * RUNTIME STATUS: see README.md "opencode 2.x" for what was observed and what was
 * only read in source. Do not extend this comment with claims; put them there, dated.
 *
 * V2 DIFFERENCES THAT BITE:
 *   - Tool names: `write` and `patch` are now `edit`; `bash` is `shell`.
 *   - Instructions: V2 reads AGENTS.md only. "It does not use CLAUDE.md as a fallback."
 *   - A blocked call is a thrown Error from `execute.before`; the message is what the
 *     model sees, so it says what to do next.
 */

import { Plugin } from "@opencode/plugin"

// Per-session set of file paths that have been read this session.
const readPaths = new Map<string, Set<string>>()

function argPath(input: any): string | undefined {
  return input?.filePath ?? input?.path ?? input?.file
}

const PREFLIGHT =
  "[Mycelium preflight] Discipline harness active. " +
  "Project state in .claude/ (canvas, diamonds, memory). " +
  "Read before Write on canvas files. Discovery before delivery."

const REFLEXION =
  " [Mycelium reflexion] This tool call FAILED. Do not retry blindly: say what failed " +
  "and why, name the root cause, then make one specific fix. If the mistake is about " +
  "this project, record it in .claude/memory/corrections.md."

export default Plugin.define({
  id: "mycelium",
  async setup(ctx) {
    // ---- Preflight context injection (every request, TUI + headless) ----
    await ctx.session.hook("context", (event) => {
      // Opt-out: weak local models (≈8B) can be distracted by the preflight prose
      // (V1 e2e 2026-06-16: 8B followed 3/3 with preflight off vs 1/3 on).
      if (process.env.MYCELIUM_PREFLIGHT === "off") return
      if (event.system.some((part) => part.text.includes("[Mycelium preflight]"))) return
      event.system.push({ type: "text", text: PREFLIGHT })
    })

    // ---- Read-before-edit guard ----
    await ctx.tool.hook("execute.before", (event) => {
      const p = argPath(event.input)
      if (event.tool === "read" && p) {
        if (!readPaths.has(event.sessionID)) readPaths.set(event.sessionID, new Set())
        readPaths.get(event.sessionID)!.add(p)
        return
      }
      if (event.tool === "edit" && p) {
        const seen = readPaths.get(event.sessionID)
        if (!seen || !seen.has(p)) {
          throw new Error(
            `Mycelium guardrail: refusing ${event.tool} on '${p}' — no prior read in this ` +
              `session. Read the file first (stale-state-edit prevention).`,
          )
        }
      }
    })

    // ---- Reflexion on tool failure (the #27900 gap, closed by V2) ----
    await ctx.tool.hook("execute.after", (event) => {
      if (event.status !== "error") return
      if (process.env.MYCELIUM_TRACE) {
        console.error(`[mycelium] tool failure observed: ${event.tool}: ${event.error.message}`)
      }
      try {
        // Tool.Error carries a `message`; append the reflexion prompt so it reaches
        // the model with the failure. If the runtime makes the field read-only this
        // throws, and the failure still propagates unchanged.
        ;(event.error as any).message = event.error.message + REFLEXION
      } catch {
        /* read-only error object: degrade to the unmodified failure */
      }
    })
  },
})
