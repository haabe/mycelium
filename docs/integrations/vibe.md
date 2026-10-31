# Using Mycelium with Mistral Vibe

**Audience**: developers who use [Mistral Vibe](https://github.com/mistralai/mistral-vibe) as their coding agent and want Mycelium's product-thinking discipline there.
**Time to read**: 5 min.
**Last updated**: 2026-10-31.
**Status**: Works, with two setup steps. Since 0.332.0 the plugin folder loads in Vibe as it ships, and one command declares Mycelium's gates in your project, so they block risky calls on Vibe too. The operating contract reaches the model through an `AGENTS.md` copy. What Vibe has no event for (session start, each prompt, the end of a turn) does not run. Details and limits below.

## Setup

Vibe has no plugin installer. A plugin is a folder under `<project>/.vibe/plugins/<name>/` (one project, trusted folders only) or `~/.vibe/plugins/<name>/` (every project).

```bash
# 1. Get Mycelium somewhere outside your project; it is the source, not your project.
git clone https://github.com/haabe/mycelium ~/src/mycelium

# 2. Copy the plugin into your project's Vibe plugins folder.
cd ~/my-project
mkdir -p .vibe/plugins
cp -R ~/src/mycelium/plugins/mycelium .vibe/plugins/mycelium

# 3. Declare Mycelium's gates in the project's .vibe/hooks.toml.
python3 .vibe/plugins/mycelium/integrations/vibe/install_hooks.py

# 4. The AGENTS.md contract copy (section below).
```

Run `vibe` from the project and trust the folder when asked; with `vibe -p`, pass `--trust`. Vibe reads a project's plugins, its `hooks.toml` and its `AGENTS.md` only in a trusted folder.

**After updating Mycelium**, copy the folder again and re-run steps 3 and 4. Step 3 replaces its own two entries and leaves the rest of your `hooks.toml` alone.

Before 0.332.0 step 2 also deleted the copy's `.codex-plugin` folder. That is no longer needed: the plugin now carries a manifest in Vibe's native format, and Vibe reads it in place of the other two.

## What works on Vibe

| Capability | Status | Notes |
|---|---|---|
| Canvas YAML, memory, decision-log, corrections, patterns | ✅ Portable | Plain files. |
| Validators (`validate_canvas.py` and the rest) | ✅ Run unchanged | Python and Bash, nothing runtime-specific. |
| Skills | ✅ As shipped | The root `plugin.json` is an [Agent Plugins](https://agent-plugins.org) 1.0 manifest, which Vibe reads before the Claude Code and Codex ones, so the folder loads as it is. Whether Vibe resolves the `${CLAUDE_PLUGIN_ROOT}` paths inside skill bodies was not measured. |
| Gates before a tool call (secret check, discovery, scale lock, scope, guard state and the rest) | ✅ After setup step 3 | Mycelium's own Claude Code hooks, run through a translator Vibe calls before each tool call. A refusal reaches the model as the call's error. |
| Checks after a tool call (canvas schema check, nudges, logs) | ✅ After setup step 3 | Their notes reach the model with the call's result. |
| Operating contract (the always-on rules) | ⚠️ By setup step 4 | Claude Code delivers it with a session-start hook. Vibe has none, so it goes in an `AGENTS.md`. |
| Per-prompt context, end-of-turn checks, reflexion on tool failure | ⛔ No route | Vibe's hook types are `pre_tool`, `post_tool` and `post_agent`. There is no session-start or prompt event, and the end-of-turn checks are not translated. |

## How the gates run on Vibe

Vibe 3.0 runs no hook a plugin ships: hooks declared inside a plugin are withheld ("neither has an execution adapter yet", in Vibe's source at 3.0.1 to 3.0.3). It runs the hooks declared in a project's `.vibe/hooks.toml` or in `~/.vibe/hooks.toml`. So `install_hooks.py` writes two entries into the project's file, and each runs `integrations/vibe/vibe_hook.py` from your copy of the plugin by its absolute path:

- `mycelium-pre-tool`, before every tool call, with `strict = true`. If the translator itself cannot run, Vibe refuses the call. That is what Mycelium's blocking hooks do in Claude Code when they cannot run.
- `mycelium-post-tool`, after every tool call that ran.

The translator maps Vibe's call to the call Mycelium's hooks were written for, runs the hooks listed for it in the plugin's `hooks/hooks.json`, and maps their answer back:

| Vibe tool | Read as | |
|---|---|---|
| `file_system.bash`, `process.start` | `Bash` | the command |
| `file_system.write_file` | `Write` | `path` as the file, and the content |
| `file_system.edit` | `Edit` | the file, the old and the new text |
| `file_system.read_file` | `Read` | `path` as the file |

Other tools (search, web fetch, subagents) run no Mycelium hook. A relative path is resolved against the folder the call runs in.

Your own entries in `hooks.toml` stay as they are. The project file, not `~/.vibe/hooks.toml`: the user file would start the translator on every tool call in every project you open with Vibe. Mycelium's hooks do nothing in a project without `.claude/canvas/` or `.claude/diamonds/`, but the translator would still start each time.

## Limitations, in plain terms

- **Where Claude Code would ask you, Vibe refuses.** A few of Mycelium's checks put a question to you rather than to the agent, for example before the agent writes a file that switches a hook off. A Vibe hook can only allow or refuse, so on Vibe the call is refused and the message tells the agent to ask you, and that you make the change yourself.
- **Advice before a call arrives after it.** Some checks warn without refusing, such as the shell-safety warnings. In Claude Code the agent sees the warning as it makes the call. On Vibe, the only text a hook can show the model before a call is a refusal, so the warning is kept and handed to the model with the call's result.
- **There is no session-start hook.** In Claude Code, Mycelium's rules are injected at the start of every session. Vibe has no event for that, so nothing loads them unless you put them in an `AGENTS.md` (below).
- **Rules that name a hook Vibe does not run are only rules here.** The contract was written for Claude Code. The end-of-turn checks (for example, that a turn ends on one next action) do not run on Vibe. The model has to follow those rules itself.
- **Plugin "knowledge" did not reach the model.** A knowledge entry in a native plugin was not in the model's context in the 2026-10-21 runs, and the model could not recall it. Why was not established.

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

**2026-10-21**, Vibe 3.0.0 from Homebrew (source read at 3.0.1), a local `llama3.1:8b` through Ollama with a 32k context, one machine, one prompt per test:
- As shipped, with both a Claude Code and a Codex manifest, Vibe dropped the plugin as ambiguous.
- With a root Agent Plugins manifest added beside both, it loaded the plugin with no warning.
- A plugin's own hooks never ran, native or adapted.
- Mycelium's secret check, declared in the project's `.vibe/hooks.toml` behind an earlier, smaller translator, refused a command that wrote a key to a file, and its message reached the model. The model then read the key from an environment variable instead, which the check allows.
- The `AGENTS.md` measurements are from the same day.

**2026-10-31**, for 0.332.0, on Vibe 3.0.3, without a model:
- **Vibe's source:** it still prefers a root Agent Plugins manifest, and still withholds plugin hooks.
- **Vibe's own plugin inspector:** it reads the shipped folder as a valid Agent Plugins 1.0 plugin, 63 skills, no diagnostics.
- **Vibe's own `hooks.toml` loader:** it reads the file `install_hooks.py` writes, beside a project's own hook, with no issue.
- **The translator,** given Vibe-shaped calls, against the plugin's real hooks in a test project:
  - it refused a shell command carrying a key;
  - it refused a write to a guard file, with the "cannot ask" message;
  - it refused a new source file in a project with no discovery state yet;
  - it passed `ls`;
  - it handed a shell-safety warning to the model with the call's result.
  These cases are `tests/python/test_vibe.py`.
- **Live sessions, inconclusive on the gates:** five one-prompt runs on the shipped folder with hooks installed by `install_hooks.py`, through four local Ollama models (llama3.1:8b, qwen3.5:9b, qwen2.5-coder:14b, mistral-nemo). In every run the plugin loaded, with Mycelium's skills in the model's prompt and no format warning. In none did the model make a tool call: it wrote the call as text, refused the request itself, or said it had done the work. So no call reached the translator, and the gates in a live 0.332.0 session are not yet shown. The 2026-10-21 live run used the earlier translator, with one gate.

A stronger model may follow the contract better than an 8B one; that was not tested.

**Codex and Claude Code read the new root manifest too.**
- **Codex** (0.150 and later, source read at 0.166.0) reads a root Agent Plugins `plugin.json` first. It takes hooks from that manifest's `com.openai` extension or, when there is none, from `.codex-plugin/plugin.json`. Mycelium's root manifest carries no `com.openai` extension, so Codex keeps its hooks. Installed from a test marketplace with and without the file, Codex 0.166.0 listed the same 63 skills. Whether Codex then runs the hooks was not run: that needs the hooks trusted, which this check did not do.
- **Claude Code** reads `.claude-plugin/plugin.json`, and `claude plugin validate` passes with the root file present.

Other runtimes: [Claude Code](../install-paths.md), [Codex](codex.md), [opencode](opencode.md), [Cursor](cursor.md).
