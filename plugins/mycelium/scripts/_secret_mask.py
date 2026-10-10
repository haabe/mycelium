"""Best-effort masking of obvious secret shapes in text a log keeps (v0.318.0).

Moved here from shell_safety_guard.py so the reflexion log masks with the same rules. It knows
token prefixes, auth headers, secret-named assignments and flags, and credentials inside a URL.
A secret in none of those shapes is kept as typed (`mysql -pHunter2` is), which is why every log
that uses this keeps command text only when the user opts in with MYCELIUM_LEDGER_TRIGGER=on.
"""

from __future__ import annotations

import re

SECRET_SHAPES = (
    # provider-shaped tokens
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}"
               r"|xox[abprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,})"),
    # Authorization headers
    re.compile(r"(?i)\b((?:bearer|basic|token)\s+)[A-Za-z0-9._~+/=-]{8,}"),
    # NAME=value where the name says it is a secret
    re.compile(r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|CREDENTIALS?)[A-Z0-9_]*=)\S+"),
    # --password x / --token=x style flags
    re.compile(r"(?i)(--?(?:password|passwd|token|secret|api-?key)[= ])\S+"),
    # credentials inside a URL
    re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@"),
)

#: The switch that lets a log keep command text at all. Off unless the user sets it.
OPT_IN_ENV = "MYCELIUM_LEDGER_TRIGGER"


def mask(text: str, limit: int) -> str:
    """The first `limit` characters of `text`, whitespace collapsed, obvious secrets replaced."""
    for pat in SECRET_SHAPES:
        text = pat.sub(lambda m: (m.group(1) if m.lastindex else "") + "<masked>", text)
    return " ".join(text.split())[:limit]


def opted_in(environ) -> bool:
    return str(environ.get(OPT_IN_ENV, "")).lower() == "on"
