"""What a Claude Code settings file switches off, or loosens, for Mycelium (v0.322.6).

WHY THIS EXISTS. Three environment variables loosen a Mycelium stop (`MYCELIUM_GUARD_STATE_EDIT`,
`MYCELIUM_NEXT_ACTION_CHECK`, `MYCELIUM_TODAY`), and a hook cannot tell who set a variable. Claude
Code writes the `env` block of a settings file into the session's environment, re-reads the file
while the session runs, and takes two more keys that end every hook at once: `disableAllHooks`,
and `enabledPlugins` with the plugin set to false (its documentation, read 2026-10-12). Until
0.322.6 no Mycelium gate looked at those files: replayed 2026-10-12 on 0.322.1, a tool call that
put `MYCELIUM_GUARD_STATE_EDIT` into `.claude/settings.local.json` drew no decision from any gate,
while a write to `discovery-skip-ack` in the same replay was asked about. The files that switch a
stop off are the person's to write, and this is one more of them. It is judged by WHAT the write
leaves in it, because the same file holds ordinary settings an agent edits all the time.

Claude Code has its own protection for `.claude/` (a prompt in the manual modes, a classifier in
auto mode, none with permissions bypassed). This does not replace it and does not depend on it.

Pure functions. Their callers: `_hook_input.guard_state_check` (a file tool, before the write)
and `bash_state_guard.py` (a shell command, compared before and after).
"""

from __future__ import annotations

import json
import os
import re

#: The project's two settings files. The user-level file is `user_settings_path()`.
SETTINGS_REL = (".claude/settings.json", ".claude/settings.local.json")
USER_SETTINGS_NAME = "~/.claude/settings.json"

#: Variables Mycelium's hooks read that are not named MYCELIUM_*: where the project is and where
#: the plugin is. Pointing either elsewhere moves every hook off the project or off its own code.
_OTHER_ENV = ("CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_ROOT")
_PLUGIN = "mycelium"
_WORDS = re.compile(r"MYCELIUM_[A-Z0-9_]+|CLAUDE_PROJECT_DIR|CLAUDE_PLUGIN_ROOT|disableAllHooks"
                    r"|mycelium@[\w.-]+", re.IGNORECASE)
_UNPARSED = "(not valid JSON) "
_ENV, _HOOKS_OFF, _PLUGINS = "env.", "disableAllHooks", "enabledPlugins."

#: The key Claude Code's own commands write (`/plugin`, `claude plugin disable`). A shell command
#: that leaves the plugin switched off is reported and never undone: the person may have run it.
WRITTEN_BY_THE_RUNTIME = _PLUGINS


def user_settings_path() -> str:
    """`~/.claude/settings.json`, or under `CLAUDE_CONFIG_DIR` when that is set."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "settings.json")


def _is_mycelium_env(name: str) -> bool:
    upper = name.upper()
    return upper.startswith("MYCELIUM_") or upper in _OTHER_ENV


def switches(text: str) -> dict:
    """Each thing in this settings text that switches Mycelium off or changes how its hooks
    decide, as `{key: value}`: `env.NAME`, `disableAllHooks`, `enabledPlugins.mycelium@...`.

    Every `MYCELIUM_*` variable counts, not only today's three: a hook cannot know which variable
    a later release will read, and a variable that loosens nothing costs the person one answer.
    Text that is not a JSON object is judged by its words, since Claude Code may read what `json`
    does not."""
    if not text.strip():
        return {}
    try:
        doc = json.loads(text)
    except ValueError:
        return _by_words(text)
    if not isinstance(doc, dict):
        return _by_words(text)
    out: dict = {}
    env = doc.get("env")
    if isinstance(env, dict):
        out.update({_ENV + str(k): v for k, v in env.items() if _is_mycelium_env(str(k))})
    elif env is not None:
        out.update(_by_words(json.dumps(env)))
    if doc.get(_HOOKS_OFF):
        out[_HOOKS_OFF] = True
    plugins = doc.get("enabledPlugins")
    if isinstance(plugins, dict):
        out.update({_PLUGINS + str(k): False for k, v in plugins.items()
                    if str(k).lower().split("@")[0] == _PLUGIN and not v})
    return out


def _by_words(text: str) -> dict:
    return {_UNPARSED + m.group(0): True for m in _WORDS.finditer(text)}


def newly_set(before: dict, after: dict) -> list[str]:
    """The keys `after` sets that `before` did not set to the same value, sorted. A switch that
    was removed is not one: taking a switch out tightens."""
    return sorted(k for k, v in after.items() if k not in before or before[k] != v)


def describe(keys: list[str], now: dict) -> str:
    """The switches as a person would read them in the file: `env.MYCELIUM_TODAY=2020-01-01`."""
    return ", ".join(k if k.startswith(_UNPARSED) else f"{k}={json.dumps(now[k]).strip(chr(34))}"
                     for k in keys)


class CannotTellError(Exception):
    """The call's effect on the file cannot be worked out from its input."""


def _apply(text: str, edits) -> str:
    for raw in edits if isinstance(edits, list) else [edits]:
        e = raw if isinstance(raw, dict) else {}
        old = e.get("old_string", e.get("oldText"))
        new = e.get("new_string", e.get("newText"))
        if not isinstance(old, str) or not isinstance(new, str) or old not in text:
            raise CannotTellError
        text = text.replace(old, new) if e.get("replace_all") else text.replace(old, new, 1)
    return text


def proposed_text(tool_input: dict, before: str, key: str, read_source) -> str:
    """The text a file tool would leave in a settings file. `key` is the input key that named the
    file; `read_source` reads the other file of a move or copy. Raises CannotTellError when the
    input is not a shape whose result can be worked out, which the caller treats as a switch."""
    if key == "destination":
        try:
            return read_source(str(tool_input.get("source") or ""))
        except OSError as exc:
            raise CannotTellError from exc
    if "content" in tool_input:
        return str(tool_input["content"])
    if "old_string" in tool_input or "oldText" in tool_input:
        return _apply(before, tool_input)
    if "edits" in tool_input:
        return _apply(before, tool_input["edits"])
    raise CannotTellError


def without(after_text: str, before: dict, keys: list[str]) -> str | None:
    """`after_text` with each of `keys` set back to what `before` held, or removed when `before`
    did not hold it. Everything else in the file is kept as it is. None when the text is not a
    JSON object or a key is not one this can set back (the unparsed kind): the caller then says
    the file could not be put back, and leaves it alone."""
    try:
        doc = json.loads(after_text)
    except ValueError:
        return None
    if not isinstance(doc, dict) or any(k.startswith(_UNPARSED) for k in keys):
        return None
    for key in keys:
        if key == _HOOKS_OFF:
            holder, name = doc, _HOOKS_OFF
        else:
            top, name = key.split(".", 1)
            holder = doc.get(top)
            if not isinstance(holder, dict):
                return None
        if key in before:
            holder[name] = before[key]
        else:
            holder.pop(name, None)
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
