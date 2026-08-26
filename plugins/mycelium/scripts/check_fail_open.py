#!/usr/bin/env python3
"""Flag NEW silent-default read chains — the anti-pattern #9 signature.

WHY THIS EXISTS AND WHY IT LOOKS LIKE THE PINS FILE. `fail-open-on-absent-input`
graduated to prose in June 2026 (anti-pattern #9) and deliberately PARKED its
mechanism behind a trigger, naming the shape it wanted: "a check that flags
`except -> default -> 2>/dev/null` read chains around state reads." Instance #12 —
a SessionStart hook exiting 0 because it could not parse its input — tripped that
trigger on 2026-08-17.

Run by hand on 2026-08-18 over the seven artifacts built that session: TEN sites,
of which SIX were legitimate and THREE were real (two silent exits in the very hook
whose job is to speak, and a verdict store that discarded every human browser
verdict on a corrupt file while reporting a clean state).

THE 60% FALSE-POSITIVE RATE IS THE WHOLE DESIGN PROBLEM. A default is only a defect
when NOTHING DOWNSTREAM SAYS the check could not look — and no static scan can see
that, because it depends on what the caller does with the value. A version that
flagged all ten would be muted inside a week, which is this repo's most-repeated
failure and would be especially stupid here, in the check named after it.

So it works like `dependency-pins.yml`: every known site is REVIEWED once, with a
reason, and the check reports only sites that are NEW. Silence means "nothing has
appeared since the last review", never "there are no defaults".

THE RULE THE REVIEWS ENCODE: it is not "never default". It is "never default
SILENTLY AT THE LAST LAYER THAT COULD SPEAK."
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys

import yaml

DEFAULT_ROOTS = ["plugins/mycelium/scripts", "plugins/mycelium/hooks"]
REVIEWED = pathlib.Path("plugins/mycelium/harness/fail-open-reviewed.yml")

EXCEPT = re.compile(r"^\s*except\b")
BENIGN = re.compile(r"return\s+(OK|True|\{\}|\[\]|''|\"\")|sys\.exit\(0\)|^\s*pass\s*$|return None")
SPEAKS = re.compile(r"print\(|WARNING|warn|stderr|UNKNOWN|systemMessage|echo ")


def sites(roots: list[str]) -> list[dict]:
    found = []
    for r in roots:
        base = pathlib.Path(r)
        if not base.is_dir():
            continue
        for p in sorted(list(base.glob("*.py")) + list(base.glob("*.sh"))):
            lines = p.read_text(encoding="utf-8", errors="ignore").split("\n")
            for i, line_text in enumerate(lines):
                if not EXCEPT.search(line_text):
                    continue
                window = "\n".join(lines[i + 1:i + 6])
                if not BENIGN.search(window):
                    continue
                # ID IS CONTENT-BASED, NOT LINE-BASED, AND THAT IS NOT A DETAIL.
                # The first version keyed on `file:line`. Fixing the nudge shifted its
                # handlers down seven lines and both reviewed sites instantly reported
                # as NEW — a register that invalidates itself whenever anything above it
                # is edited produces noise on first contact and gets muted, which is the
                # failure this check is named after. The key is the handler's own text.
                sig = hashlib.sha1(  # noqa: S324 - content id, not a security digest

                    re.sub(r"\s+", " ", "\n".join(lines[i:i + 4])).strip().encode()
                ).hexdigest()[:10]
                found.append({
                    "id": f"{p.name}@{sig}",
                    "file": str(p),
                    "line": i + 1,
                    # Whether anything in the handler SPEAKS is the single strongest
                    # signal available statically. It is a hint for the reviewer, never
                    # a verdict: a handler can stay silent and still be correct when its
                    # caller reports, which is why review is a human step.
                    "speaks": bool(SPEAKS.search(window)),
                })
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS)
    ap.add_argument("--reviewed", default=str(REVIEWED))
    ap.add_argument("--strict", action="store_true", help="exit 1 on an unreviewed site")
    args = ap.parse_args(argv)


    rp = pathlib.Path(args.reviewed)
    known = {}
    if rp.exists():
        try:
            known = {e["id"]: e for e in (yaml.safe_load(rp.read_text()) or {}).get("reviewed", [])}
        except (yaml.YAMLError, TypeError, KeyError) as e:
            # Reporting rather than defaulting to {} — an unreadable registry would
            # otherwise make every known site look new, which is the loud direction but
            # still a lie about what was checked.
            print(f"ERROR: {rp} is unreadable ({type(e).__name__}); refusing to guess.",
                  file=sys.stderr)
            return 2

    found = sites(args.roots)
    new = [s for s in found if s["id"] not in known]

    print("Fail-open scan (anti-pattern #9 signature)")
    print("=" * 60)
    # ZERO SCANNED SCRIPTS IS NOT ZERO FAIL-OPENS. Added 2026-08-25: on CI run 32860858081
    # this printed "0 default-on-exception sites, 0 reviewed, 0 NEW" and exited 0, because the
    # roots did not resolve from the workspace root. Eleven sites exist. A check that reports
    # a clean scan of nothing is itself the anti-pattern it hunts, which is the third time this
    # exact shape was found in one day (see check_yaml_duplicate_keys, check_touch_log_order).
    scanned = [r for r in args.roots if pathlib.Path(r).exists()]
    if not scanned:
        print("  UNKNOWN - none of the scan roots exist from here, so NOTHING was scanned and "
              "this is NOT a clean result.")
        print(f"  roots={list(args.roots)}  cwd={pathlib.Path.cwd()}")
        return 1
    print(f"  {len(found)} default-on-exception sites, {len(known)} reviewed, {len(new)} NEW")

    if new:
        print("\nNEW — each needs one judgement: when this handler fires, does ANYTHING\n"
              "downstream tell a human the check could not look? If yes, review it as\n"
              "accepted with that reason. If no, it is a fail-open and it must speak.")
        for s in new:
            hint = "handler appears to speak" if s["speaks"] else "handler is SILENT"
            print(f"  {s['id']:<44} {hint}\n     {s['file']}:{s['line']}")
        print(f"\n  Record judgements in {rp} under `reviewed:` with id + reason.")
    else:
        print("\n  No new sites since the last review. This is NOT 'there are no defaults' —\n"
              "  it is 'none have appeared that a human has not already ruled on'.")

    return 1 if (args.strict and new) else 0


if __name__ == "__main__":
    raise SystemExit(main())
