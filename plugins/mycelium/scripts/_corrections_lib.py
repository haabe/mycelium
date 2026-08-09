"""One definition of "a correction entry", shared by everything that counts them.

WHY THIS EXISTS
---------------
Three shipped artifacts counted the entries in `.claude/memory/corrections.md`,
and on 2026-08-09 they returned three different numbers for the same file:

    hooks/preflight.sh              `grep -c '^### '`                    100
    check_cluster_reconcile.py      `^#{2,4}\\s+DATE[a-z]?`               103
    check_correction_attribution.py headings (2-3) OR bullet form         141

Four independent divergences produced that spread, and each one is a small,
defensible-looking choice made in isolation:

  1. HEADING DEPTH. The attribution script accepted `##`-`###`; the cluster
     script accepted `##`-`####`. A `####` entry is real and only one saw it.
  2. THE DATE SUFFIX. corrections.md carries `2026-08-02b` — a second entry on
     a day that already had one. The cluster script allowed the trailing letter;
     the attribution script ended its date with `\\b`, which cannot match between
     `2` and `b`, so it dropped exactly those entries.
  3. THE BULLET FORM. `- **Title (2026-05-03, class)**: ...` is a real entry
     shape used heavily in the recent corpus. Only the attribution script knew
     it. This alone accounted for most of the spread.
  4. THE BANNER MATCHED NO DATE AT ALL. `^### ` counts every third-level
     heading, so it missed `##` entries AND counted section headings like
     `### Prevention rule` as entries. Wrong in both directions at once.

WHY IT MATTERS MORE THAN ITS SIZE
---------------------------------
The preflight banner prints its number into every session's context, before any
work starts. It is the first quantity an agent or the founder sees, and it is
the denominator behind any felt sense of how much correction history exists. It
also drifted monotonically worse: measured 2026-08-08 the gap was 30, measured
2026-08-09 it was 41.

THIS IS THE SAME DEFECT, THIRD INSTANCE, AND THAT IS THE POINT
---------------------------------------------------------------
corrections.md records this exact bug against the attribution script on
2026-08-03 ("The script written to print an honest denominator had a wrong
denominator" — 75 headings matched, 26 bullets invisible). It was fixed there in
v0.80.1. `check_cluster_reconcile.py` then shipped in v0.99.0 on 2026-08-06 —
three days AFTER that fix — carrying the identical blind spot, because the fix
lived in one file's regex and nothing named the format itself.

So the remedy is not a fourth correct regex. It is one definition plus a fixture
that every counter is tested against, so the next counter someone writes fails
loudly instead of being quietly wrong. See
`tests/fixtures/corrections/mixed.md` and
`tests/python/test_correction_count_agreement.py`.

THE BASH HOOK CANNOT IMPORT THIS MODULE, and pretending otherwise would be the
same mistake at one remove. `hooks/preflight.sh` carries an ERE that must stay
equivalent to `ENTRY_RE` below; the agreement test runs the real hook against
the real fixture and compares its banner to this module's count, so a drift
between the two is a test failure rather than a discrepancy nobody measures.
"""

from __future__ import annotations

import re

#: The canonical entry pattern. Both shapes the corpus actually uses.
#:
#:   heading style  `## 2026-05-03 — thing that happened`
#:                  `#### 2026-08-02b - second entry that day`
#:   bullet style   `- **Thing that happened (2026-05-03, some-class)**: ...`
#:
#: Heading depth is 2-4 and the date may carry a single trailing letter, because
#: both of those are in the live corpus. A heading with no date is NOT an entry:
#: `### Prevention rule` is a section inside an entry, and counting it is how the
#: banner over-reported while under-reporting at the same time.
ENTRY_RE = re.compile(
    r"^#{2,4}[ \t]+(\d{4}-\d{2}-\d{2})([a-z]?)(?![\w-])[^\n]*$"      # heading
    r"|"
    r"^-[ \t]+\*\*[^\n]*?\((\d{4}-\d{2}-\d{2})([a-z]?)[,)][^\n]*$",  # bullet
    re.MULTILINE,
)

#: The POSIX ERE equivalent, for the bash hook. Kept beside the Python pattern
#: so the two are read together and diverge visibly rather than silently. The
#: agreement test asserts they return the same count on the fixture; it does NOT
#: assert the strings are equal, because grep and `re` are not the same dialect
#: (no `\d`, no lookahead in ERE) and demanding identical text would force one
#: of them to be written badly.
ENTRY_ERE = (
    r"^#{2,4}[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"|"
    r"^-[[:space:]]+\*\*.*\([0-9]{4}-[0-9]{2}-[0-9]{2}[a-z]?[,)]"
)


def entry_marks(text: str) -> list[re.Match[str]]:
    """Every entry start, in document order."""
    return list(ENTRY_RE.finditer(text))


def entry_date(match: re.Match[str]) -> str:
    """The ISO date of an entry, WITHOUT any trailing disambiguation letter.

    Group 1 is the heading date and group 3 the bullet date; exactly one of the
    two alternatives matched, so one of them is always None.
    """
    return match.group(1) or match.group(3)


def entry_dates(text: str) -> list[str]:
    """Dates of every entry, in document order. Duplicates preserved."""
    return [entry_date(m) for m in entry_marks(text)]


def entries(text: str) -> list[tuple[str, str]]:
    """(date, body) per entry. A body runs to whichever entry starts next.

    Mixed files interleave correctly because the terminator is "the next entry
    of EITHER shape", not "the next heading".
    """
    marks = entry_marks(text)
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((entry_date(m), text[m.start():end]))
    return out


def count(text: str) -> int:
    """How many correction entries `text` contains."""
    return len(entry_marks(text))
