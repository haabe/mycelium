# Using Mycelium with Mistral Vibe

**Audience**: developers who use [Mistral Vibe](https://github.com/mistralai/mistral-vibe) as their coding agent and want Mycelium's product-thinking discipline there.
**Time to read**: 5 min.
**Last updated**: 2026-10-21.
**Status**: Partly works, with setup by hand. Mycelium does not yet ship anything for Vibe. Installed the way Vibe's docs describe, it loads nothing at all. With the steps below, the skills load and the operating contract reaches the model. The gates, which block risky actions in Claude Code, do not run unless you wire them yourself. Everything here was measured on Vibe 3.0.0 on 2026-10-21. Details and limits are below.

## What happens if you just install it

Vibe has no plugin installer. A plugin is a folder under `~/.vibe/plugins/<name>/` (every project) or `<project>/.vibe/plugins/<name>/` (one project, trusted folders only).

Mycelium's plugin folder carries two manifests: one for Claude Code (`.claude-plugin/`) and one for Codex (`.codex-plugin/`). Vibe 3.0 can adapt either one, but when it finds both it reports the plugin as `format_ambiguous`, a fatal issue, and **drops the whole plugin**. You get no skills, no hooks and no contract. In a headless run the warning appears in the run's export; we did not check what the interactive screen shows.

## What works on Vibe 3.0

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Portable | Plain files. |
| Validators (`validate_canvas.py` and the rest) | ✅ Run unchanged | Python and Bash, nothing runtime-specific. |
| Skills | ⚠️ After setup step 2 | With the Codex manifest removed from your copy, Vibe adapts Mycelium as a Claude Code plugin and loads every skill but one. The one left out is `ping`, a smoke test marked not for the model to call (`disable-model-invocation`); that is the likely reason, not a confirmed one. Whether Vibe resolves the `${CLAUDE_PLUGIN_ROOT}` paths inside skill bodies was not measured. |
| Operating contract (the always-on rules) | ⚠️ By the workaround below | Claude Code delivers it with a session-start hook. Vibe has none, so it goes in an `AGENTS.md`. |
| Gates (secret check, read-before-edit, scope and the rest) | ⛔ Not shipped | Vibe 3.0 runs no hook a plugin ships. One of Mycelium's gates was made to block on Vibe by declaring it in the project's `.vibe/hooks.toml` behind a small format translator. Mycelium does not ship that translator yet. |
| Per-prompt context, stop check, reflexion on tool failure | ⛔ No route found | Vibe's hook types are `pre_tool`, `post_tool` and `post_agent`. There is no prompt-submit or tool-failure event. |

**Net**: on Vibe, Mycelium's discipline runs as instructions the model follows, not as checks that stop it. How well that holds depends on the model.

## Limitations, in plain terms

- **There is no session-start hook.** In Claude Code, Mycelium's rules are injected at the start of every session. Vibe has no event for that, so nothing loads them unless you put them in an `AGENTS.md` (below).
- **Hooks shipped inside a plugin do not run.** This holds for a Claude Code plugin's hooks and for Vibe's own native plugin format. Vibe 3.0.1's source says hook bindings are withheld until an execution adapter exists. Only hooks declared in a project or user `hooks.toml` run.
- **Plugin "knowledge" did not reach the model.** A knowledge entry in a native plugin was not in the model's context, and the model could not recall it. Why was not established.
- **Rules that name a hook are only rules here.** The contract was written for Claude Code. Where it says a hook blocks something, nothing on Vibe blocks it; the model has to follow the rule itself.

## Setup

These are the steps that were measured: project scope, a trusted folder.

```bash
# 1. Get Mycelium somewhere outside your project; it is the source, not your project.
git clone https://github.com/haabe/mycelium ~/src/mycelium

# 2. Copy the plugin into your project's Vibe plugins folder and remove the Codex
#    manifest from YOUR COPY, so Vibe sees one manifest and loads the skills.
cd ~/my-project
mkdir -p .vibe/plugins
cp -R ~/src/mycelium/plugins/mycelium .vibe/plugins/mycelium
rm -rf .vibe/plugins/mycelium/.codex-plugin

# 3. The AGENTS.md contract copy (next section).
```

Run `vibe` from the project and trust the folder when asked; with `vibe -p`, pass `--trust`. Vibe reads a project's plugins and its `AGENTS.md` only in a trusted folder.

## The workaround for the missing session-start hook: the AGENTS.md contract copy

Vibe puts `AGENTS.md` files into the model's instructions: the one at the root of a trusted project, and a user-level one at `$VIBE_HOME/AGENTS.md` (`~/.vibe/AGENTS.md` by default) that applies to every project. Mycelium's operating contract is a single file, `engine/agent-operating-contract.md`. Copy it into the project's `AGENTS.md`, replacing its `${CLAUDE_PLUGIN_ROOT}` placeholders with the plugin's path, because only Claude Code's hook fills those in:

```bash
cd ~/my-project
python3 -c 'import sys; root = sys.argv[1]; text = open(root + "/engine/agent-operating-contract.md").read(); open("AGENTS.md", "a").write("\n" + text.replace("${CLAUDE_PLUGIN_ROOT}", root))' "$PWD/.vibe/plugins/mycelium"
```

The command appends, so an existing `AGENTS.md` keeps your own text above the contract.

- **Measured**: with the full contract (about 24 KB) in a project's `AGENTS.md`, the whole text, title to last sentence, was in the model's input, with no placeholder left. Asked with tools off, the model answered two questions from it correctly, one from its last section. A two-line test in `$VIBE_HOME/AGENTS.md` reached the model the same way.
- **Prefer the project file.** The user-level file puts Mycelium's rules into every project you open with Vibe, including ones that do not use Mycelium.
- **It is a snapshot.** After you update Mycelium, run the command again on a fresh `AGENTS.md`; otherwise the old contract stays.
- **It costs context.** The contract is about 6,000 tokens in every session.

## How this was measured

Vibe 3.0.0 from Homebrew (source read at 3.0.1), a local `llama3.1:8b` through Ollama with a 32k context, one machine, one prompt per test, 2026-10-21. The gate test used Mycelium's secret check: declared in the project's `.vibe/hooks.toml` behind the translator, it refused a command that wrote a key to a file. The model then read the key from an environment variable instead, which the check allows. A stronger model may follow the contract better than an 8B one; that was not tested.

Other runtimes: [Claude Code](../install-paths.md), [Codex](codex.md), [opencode](opencode.md), [Cursor](cursor.md).
