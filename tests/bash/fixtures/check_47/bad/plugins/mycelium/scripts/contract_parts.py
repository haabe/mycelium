#!/usr/bin/env python3
"""Deliver the operating contract in parts that fit a hook's context cap (v0.310.16).

WHY THIS EXISTS. Claude Code caps a hook's `additionalContext` at 10,000 characters. Over the
cap it saves the output to a file and puts a 2,000-character preview in context, and it does not
ask the model to read the file. Until v0.310.16 session-start.sh sent the whole contract
(about 22,000 characters) plus the reminders as ONE string, so most sessions got the contract's
first section and nothing after it, while every check reported the contract as injected. Found
by a review against the plugins reference on 2026-10-03 and confirmed in that session's own
transcript ("<persisted-output> Output too large (25.7KB) ... Preview (first 2KB)").

HOW. The contract is split between its `## ` sections into parts of at most PART_LIMIT
characters, header included. Each part is emitted by its own SessionStart handler
(`hooks/contract-part.sh <n>`), because the cap applies to each hook's output separately. The
handlers run in parallel, so each part says which part it is and that the parts form one
contract. A handler whose part number is past the last part emits nothing.

THE PLUGIN ROOT. `${CLAUDE_PLUGIN_ROOT}` is substituted only in hook commands and skill bodies;
it is not set in the shell Claude runs commands in. Text Claude reads (this contract, engine
docs it opens later) used it literally, so the commands it names pointed nowhere for anyone
whose own shell did not happen to export it. The parts carry the real path in place of the
literal, and part 1 states the path once so a later doc's literal can be resolved too.

`--check` is the CI guard: it fails when the contract would need more parts than there are
handlers, or a single section is larger than a part can hold.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CAP = 10_000          # Claude Code's additionalContext cap, per hook output
PART_LIMIT = 9_400    # what a part may use, header included, leaving room under the cap
MAX_PARTS = 4         # handlers registered in the hook manifests (contract-part.sh 1..4)
ROOT_LITERAL = "${CLAUDE_PLUGIN_ROOT}"

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CONTRACT = PLUGIN_ROOT / "engine" / "agent-operating-contract.md"


def header(k: int, n: int) -> str:
    return (f"MYCELIUM OPERATING CONTRACT, part {k} of {n}. The parts arrive as separate blocks, "
            "in any order; together they are one contract (engine/agent-operating-contract.md).")


def root_line(root: str) -> str:
    return (f"On this machine the Mycelium plugin root is {root}. Wherever a Mycelium file says "
            f"{ROOT_LITERAL}, use that path: the variable is not set in the shell you run "
            "commands in.")


def split(text: str, root: str) -> list[str]:
    """Greedy split between `## ` sections; each returned part includes its header."""
    text = text.replace(ROOT_LITERAL, root).strip()
    sections = [s.strip() for s in re.split(r"(?m)^(?=## )", text) if s.strip()]
    budget = PART_LIMIT - len(header(9, 9)) - len(root_line(root)) - 4  # worst-case header room
    groups: list[list[str]] = [[]]
    for sec in sections:
        if len(sec) > budget:
            raise ValueError(f"a contract section is {len(sec)} characters, over the "
                             f"{budget} a part can hold: "
                             f"{sec.splitlines()[0][:80]!r}")
        if groups[-1] and len("\n\n".join(groups[-1] + [sec])) > budget:
            groups.append([])
        groups[-1].append(sec)
    n = len(groups)
    parts = []
    for k, g in enumerate(groups, 1):
        lead = [header(k, n)] + ([root_line(root)] if k == 1 else [])
        parts.append("\n\n".join(lead + g))
    return parts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--part", type=int, help="emit SessionStart hook JSON for this part (1-based)")
    ap.add_argument("--check", action="store_true",
                    help="fail if the contract does not fit the handlers")
    ap.add_argument("--contract", default=str(CONTRACT))
    args = ap.parse_args(argv)

    try:
        text = Path(args.contract).read_text(encoding="utf-8")
        parts = split(text, str(PLUGIN_ROOT))
    except (OSError, ValueError) as e:
        if args.check:
            print(f"contract parts: FAIL: {e}")
            return 1
        return 0  # a hook never blocks a session over its own delivery

    if args.check:
        sizes = [len(p) for p in parts]
        print(f"contract parts: {len(parts)} part(s), sizes {sizes}, limit {PART_LIMIT}, "
              f"cap {CAP}, "
              f"handlers {MAX_PARTS}")
        if len(parts) > MAX_PARTS or max(sizes) > PART_LIMIT:
            print("FAIL: the contract no longer fits. Trim it, or register another "
                  "contract-part.sh "
                  "handler in every hook manifest and raise MAX_PARTS.")
            return 1
        return 0

    if args.part and 1 <= args.part <= len(parts):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": parts[args.part - 1]}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
