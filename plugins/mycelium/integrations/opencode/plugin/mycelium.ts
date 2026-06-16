/**
 * opencode-mycelium — enforcement plugin (SKELETON / STARTER)
 *
 * Ports the load-bearing slice of Mycelium's Claude Code hooks to opencode.
 * RUNTIME-VERIFIED on opencode 1.17.7 (2026-06-15): plugin loads, chat.message
 * injection works headless, tool.execute.before throw blocks the tool, and the
 * read-before-edit guard fired live against llama3.1:8b. Clean end-to-end run
 * (EXIT 0). Behaviour on other opencode versions may differ — see the README.
 *
 * Covers (the two clean hooks):
 *   - chat.message        → preflight context injection (CC: UserPromptSubmit/preflight.sh).
 *                           Fires in BOTH TUI and headless `opencode run` (gap #27899 closed).
 *   - tool.execute.before → read-before-edit guard (CC: structurally enforced Edit precondition;
 *                           opencode core does NOT enforce it — issue #27901). Load-bearing
 *                           for small FOSS models that ignore the prompt-level instruction.
 *
 * NOT covered (documented gaps / TODO):
 *   - tool failure events (reflexion) — opencode fires NO plugin hook on tool failure
 *     (issue #27900, the one hard gap). Needs the upstream tool.execute.error PR.
 *   - Stop/turn-end guardrail — portable via session.idle + chat.message relocation (not wired).
 *   - gate/scope/secret-scan (tool.execute.before) + post-write nudge/change-log/read-log
 *     (tool.execute.after) — extend the handlers below.
 *
 * CAVEATS:
 *   - chat.message part shape is version-sensitive: 1.17.7 requires id + sessionID + messageID
 *     (handled below). Older/newer opencode may differ; a rejected part aborts the run.
 *   - Tool arg field names (filePath vs path) vary by tool; the guard reads common variants.
 *     On 1.17.7 the tools are lowercase `read`/`edit` with top-level `filePath` — verified.
 *   - Small-model usability: injecting preflight prose can DISTRACT weak models (e.g. 8B) into
 *     summarising the reminder instead of calling tools. If your local model derails, trim or
 *     drop the preflight text — the read-before-edit guard does not depend on it.
 */

import type { Plugin } from "@opencode-ai/plugin"

// Per-session set of file paths that have been read this session.
const readPaths = new Map<string, Set<string>>()

function argPath(args: any): string | undefined {
  return args?.filePath ?? args?.path ?? args?.file
}

export const Mycelium: Plugin = async ({ directory }) => {
  return {
    // ---- Preflight context injection (every user message, TUI + headless) ----
    "chat.message": async (input, output) => {
      // Opt-out: weak local models (≈8B) can be distracted by the preflight prose
      // into summarising it instead of calling tools (e2e 2026-06-16: 8B followed
      // 3/3 with preflight off vs 1/3 on). Set MYCELIUM_PREFLIGHT=off to disable.
      if (process.env.MYCELIUM_PREFLIGHT === "off") return
      // Mirror of Mycelium's preflight stamp: a lightweight reminder that the
      // discipline harness is active and where project state lives.
      // Runtime-verified on opencode 1.17.7: a pushed text part MUST carry
      // `id` (prt_-prefixed), `sessionID`, and `messageID` or the session
      // aborts with a SchemaError before the model runs. Derive them from
      // output.message (.sessionID / .id) with input as fallback.
      const preflight =
        "[Mycelium preflight] Discipline harness active. " +
        "Project state in .claude/ (canvas, diamonds, memory). " +
        "Read before Write on canvas files. Discovery before delivery."
      const msg: any = (output as any).message
      const sessionID = msg?.sessionID ?? (input as any)?.sessionID
      const messageID = msg?.id ?? (input as any)?.messageID
      output.parts.push({
        id: "prt_myc_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
        type: "text",
        text: preflight,
        sessionID,
        messageID,
      } as any)
    },

    // ---- Read-before-edit guard (the #27901 enforcement opencode core lacks) ----
    "tool.execute.before": async (input, output) => {
      const { tool, sessionID } = input
      const p = argPath(output.args)

      // Track reads.
      if (tool === "read" && p) {
        if (!readPaths.has(sessionID)) readPaths.set(sessionID, new Set())
        readPaths.get(sessionID)!.add(p)
        return
      }

      // Enforce: edit/write/patch must follow a read of the same path in-session.
      if ((tool === "edit" || tool === "write" || tool === "patch") && p) {
        const seen = readPaths.get(sessionID)
        if (!seen || !seen.has(p)) {
          throw new Error(
            `Mycelium guardrail: refusing ${tool} on '${p}' — no prior Read in this ` +
              `session. Read the file first (stale-state-edit prevention).`,
          )
        }
      }
    },
  }
}
