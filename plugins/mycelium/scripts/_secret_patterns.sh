#!/bin/bash
# Mycelium's own short list of secret shapes. Sourced, never run: it defines SECRET_PATTERNS.
#
# Since 0.323.0 this list is the FALLBACK, not the scanner. What is staged, committed and pushed
# is scanned by an established scanner (gitleaks) when one is installed; this list runs in its
# place when none is, and the person is told that it is the weaker check. It is also what
# hooks/gate.sh runs over the text of a shell command, where a key typed into the command line
# would end up in logs and transcripts.
#
# POSIX CLASSES ONLY (0.318.3). These run under `grep -E`. Until 0.318.3 nine of them put `\s`
# and `\x27` INSIDE bracket expressions. GNU grep reads those as whitespace and a quote. The BSD
# grep that /usr/bin/grep is on macOS reads a backslash in a bracket as a literal character, so
# the class meant for whitespace matched the letter s and the class meant for a single quote
# matched x, 2 and 7. Whether a credential was caught depended on which letters it contained, a
# value in single quotes was not seen as quoted, and `[A-Za-z0-9_\-\.]` held no hyphen at all
# (dogfood harms check 2026-10-11). Inside a bracket: [:space:], a literal quote, a hyphen LAST.
# tests/python/test_gate_secret_scan.py runs every pattern under the system grep, both ways.
WS='[[:space:]]'
Q="[\"']"              # an opening double or single quote
NQ="[^[:space:]\"']"   # anything but whitespace and quotes
# A connection string is a secret when it carries a password: scheme://user:password@host, or a
# password= parameter. Until 0.318.3 any database URL of ten characters was refused, password or
# not.
UI="[^[:space:]\"'/@:]*:[^[:space:]\"'/@]+@"
DB='(postgres|postgresql|mysql|mongodb|mongodb\+srv|rediss?)'
# shellcheck disable=SC2034  # read by the script that sources this file
SECRET_PATTERNS=(
  "[Aa][Pp][Ii]_?[Kk][Ee][Yy]${WS}*[=:]${WS}*${Q}[A-Za-z0-9_-]{20,}"
  "[Ss][Ee][Cc][Rr][Ee][Tt]_?[Kk][Ee][Yy]${WS}*[=:]${WS}*${Q}[A-Za-z0-9_-]{20,}"
  "[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]${WS}*[=:]${WS}*${Q}${NQ}{8,}"
  "Bearer${WS}+[A-Za-z0-9_.-]{20,}"
  'sk-[A-Za-z0-9]{20,}'
  'ghp_[A-Za-z0-9]{36}'
  'gho_[A-Za-z0-9]{36}'
  'glpat-[A-Za-z0-9-]{20,}'
  'xox[bpas]-[A-Za-z0-9-]{10,}'
  'AKIA[0-9A-Z]{16}'
  'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.'
  "[Pp][Rr][Ii][Vv][Aa][Tt][Ee]_?[Kk][Ee][Yy]${WS}*[=:]${WS}*${Q}"
  "${DB}://${UI}"
  "${DB}://${NQ}*[?&]password="
)
