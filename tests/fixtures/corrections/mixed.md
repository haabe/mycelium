# Corrections — counting fixture

THIS FILE IS THE SHARED DEFINITION OF "A CORRECTION ENTRY". It is not example
data and it is not a sample of the real log. Every artifact that counts entries
in `.claude/memory/corrections.md` — the preflight banner, the attribution
script, the cluster-reconcile script, and anything written later — is tested
against this file and must return the same number.

**EXPECTED ENTRY COUNT: 8.** If you change this file, change
`tests/python/test_correction_count_agreement.py::EXPECTED` in the same commit
and say why in the message. A silent edit here weakens every counter at once.

Each shape below is here because a shipped counter got it wrong. The comment on
each says which one.

## 2026-01-01 — heading at depth two

Entry 1. `check_correction_attribution.py` accepted `##`; the preflight banner
matched `^### ` only, so every `##` entry was invisible to the first number
printed in every session.

Caught by the user.

### Prevention rule

NOT AN ENTRY. A section heading inside entry 1, at the same depth the banner
counted. The banner scored this as a correction, which is how it managed to
under-report and over-report simultaneously.

### 2026-01-02 — heading at depth three

Entry 2. The common shape. Every counter found this one, which is why the
divergence went unnoticed for so long: the majority case agreed.

Caught by the hook.

#### 2026-01-03 — heading at depth four

Entry 3. `check_cluster_reconcile.py` accepted `#{2,4}`;
`check_correction_attribution.py` accepted `#{2,3}` and dropped this.

### 2026-01-03b — a second entry on a day that already had one

Entry 4. The trailing letter is real: the live corpus carries `2026-08-02b`. The
cluster script allowed `[a-z]?`; the attribution script terminated its date with
`\b`, which cannot match between `3` and `b`, so it dropped exactly the entries
that a busy day produces.

Its date is `2026-01-03` — the suffix disambiguates the heading, it does not
make a different day, and a counter that reports `2026-01-03b` as a date will
break any comparison against a real cutoff.

### Not a dated heading at all

NOT AN ENTRY. Prose maintenance, a rubric, a table of contents. Mentioning
2026-01-04 in the body does not make this an entry — only a date in the heading
position does.

- **Bullet form with a class (2026-01-05, verification-hygiene)**: entry 5.
  This shape carries most of the recent corpus and `check_cluster_reconcile.py`
  cannot see it at all. On 2026-08-09 that single blind spot accounted for most
  of a 41-entry spread.

- **Bullet form with no class (2026-01-06)**: entry 6. The class is optional, so
  the date may be closed by `)` as well as `,`. A pattern requiring the comma
  silently drops the terser half of the bullet entries.

- **Bullet form with a suffixed date (2026-01-06b)**: entry 7. Same
  disambiguation as the heading form, and the same trap.

- This bullet is NOT an entry. No bold title, no parenthesised date — it is an
  ordinary list item inside entry 7, of the kind that appears in any body that
  enumerates anything. A pattern anchored on `^- ` alone would count it.

- **Not an entry either**: bold title, but no date in parentheses. Some bodies
  use bold-led bullets as sub-points, and treating them as entries inflates the
  count on exactly the long, carefully-written entries.

## 2026-01-07 — final entry, to prove the last body terminates at end-of-file

Entry 8. A counter that slices bodies between marks must handle the last one
running to EOF rather than to a following mark, or it returns a body of length
zero and every classifier reading that body reports "no signal".
