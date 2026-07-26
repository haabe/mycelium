"""Shared text helpers for the wiring/authenticity fitness functions.

Extracted rather than duplicated (G-V3). Both `check_test_authenticity.py` and
`check_wiring_contract.py` need to answer "does this file REFERENCE that name in
code?", and both need the same answer to "is this line a comment?" — a reference
that appears only in prose is not a call site, and treating it as one is how a
doc that merely *mentions* a script comes to look like a caller.
"""

from __future__ import annotations

import re

# Line-leading comment markers across the languages these guards read.
_COMMENT_LINE = ("#", "//", "*", '"""', "'''", "--")
_TRAILING_COMMENT = re.compile(r"\s+(?:#|//)\s.*$")


def strip_comments(text: str) -> str:
    """Drop comment-only lines and trailing comment runs.

    Deliberately crude and deliberately conservative: it is better to keep a
    little prose than to strip a line of real code, because a false "no
    reference" reads as a missing caller and sends someone hunting for a bug
    that is not there.
    """
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith(_COMMENT_LINE):
            continue
        out.append(_TRAILING_COMMENT.sub("", line))
    return "\n".join(out)


def references(code: str, name: str) -> bool:
    """True when `code` mentions `name` as a whole token.

    The lookbehind guards against WORD characters only. It must NOT exclude `/`,
    `.` or `-`: the commonest reference in a shell script or CI file is a path
    (`bash scripts/foo.sh`, `python3 plugins/.../bar.py`), where the name is
    preceded by a slash. A stricter boundary rejected exactly those and produced
    45 false "no caller" findings in one run of the sibling guard.
    """
    if not name:
        return False
    return bool(re.search(rf"(?<!\w){re.escape(name)}(?!\w)", code))
