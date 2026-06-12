#!/usr/bin/env python3
"""Static validator for render-fleet Mermaid output (pure stdlib).

Closes the render-fleet agent-blind-spot (the agent emits Mermaid syntax but
cannot visually evaluate the rendered diagram — render-conventions.md "Limit:
agent cannot visually validate"). Two deterministic checks the agent cannot do
by eye, both mechanizable with no external dependency:

  1. STATE-ID CONSISTENCY (closes F11): in a stateDiagram with explicit
     `state "..." as <ID>` declarations, every `<src> --> <dst>` endpoint and
     every `class <X> <name>` target must reference a declared ID or a Mermaid
     built-in (`[*]`). A mismatch is a render-time parse error invisible in the
     raw syntax (render-conventions.md "Mermaid state ID consistency").

  2. WCAG CONTRAST (closes F13): every foreground/background colour pair in
     a `themeVariables` init block must meet WCAG 2.1 AA 4.5:1. Contrast is
     pure math — the one accessibility check needing no rendering surface.

Optionally, when a Mermaid CLI (`mmdc`) is on PATH, `--cli` shells out to it as
a full-parse cross-check. Fail-open: absence of `mmdc` is INFO, never a failure
— the static checks above stand alone.

Usage:
    validate_mermaid.py <file>        # file with a ```mermaid block or raw diagram
    cat diagram.mmd | validate_mermaid.py -
    validate_mermaid.py <file> --cli  # also run mmdc if present

Exit 0 = no failures; exit 1 = at least one FAIL. Per G-V12, coverage proof in
tests/bash/test_validate_mermaid.sh.
"""
import re
import shutil
import subprocess
import sys
import tempfile

WCAG_AA_MIN_RATIO = 4.5  # WCAG 2.1 AA for normal text
SRGB_LINEAR_CUTOFF = 0.03928  # sRGB piecewise-linearization threshold

HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
THEMEVAR_RE = re.compile(
    r"['\"]?([A-Za-z][A-Za-z0-9]*)['\"]?\s*:\s*['\"](#[0-9A-Fa-f]{6})['\"]"
)
STATE_DECL_RE = re.compile(r"\bstate\s+(?:\"[^\"]*\"|'[^']*')\s+as\s+([A-Za-z_][\w]*)")
ARROW_RE = re.compile(
    r"^\s*([A-Za-z_]\w*|\[\*\])\s*-->\s*([A-Za-z_]\w*|\[\*\])"
)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][\w,\s]*)\s+\w+\s*$")


def extract_mermaid(text):
    """Pull the first fenced ```mermaid block, else return the whole text."""
    m = re.search(r"```mermaid\s*\n(.*?)```", text, re.DOTALL)
    return m.group(1) if m else text


def _luminance(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))

    def lin(c):
        return c / 12.92 if c <= SRGB_LINEAR_CUTOFF else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg, bg):
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _pair_name(var):
    """Map a label/text variable to the background variable it sits on.

    Convention (render-conventions.md palette): cScaleLabel4 -> cScale4,
    gitBranchLabel0 -> git0, primaryTextColor -> primaryColor.
    """
    for marker in ("BranchLabel", "Label", "TextColor", "Text"):
        if marker in var:
            base = var.replace(marker, "")
            # primaryTextColor -> primaryColor (re-attach the Color suffix)
            if marker == "TextColor":
                base += "Color"
            return base
    return None


def check_contrast(diagram):
    fails, passes = [], 0
    colors = dict(THEMEVAR_RE.findall(diagram))
    for var, fg in colors.items():
        base = _pair_name(var)
        if base and base in colors:
            bg = colors[base]
            ratio = contrast_ratio(fg, bg)
            if ratio < WCAG_AA_MIN_RATIO:
                fails.append(
                    f"FAIL: contrast {var} ({fg}) on {base} ({bg}) = {ratio:.2f}:1 "
                    f"< {WCAG_AA_MIN_RATIO}:1 WCAG AA"
                )
            else:
                passes += 1
    return fails, passes


def _declared_state_ids(diagram):
    """Collect declared state IDs: explicit `state ... as <ID>` + `ID : label`."""
    declared = set(STATE_DECL_RE.findall(diagram))
    if not declared:
        return declared
    for line in diagram.splitlines():
        m = re.match(r"^\s*([A-Za-z_]\w*)\s*:\s+\S", line)
        if m and "-->" not in line:
            declared.add(m.group(1))
    declared.add("[*]")
    return declared


def check_state_ids(diagram):
    """Only enforced when explicit `state ... as <ID>` declarations exist."""
    declared = _declared_state_ids(diagram)
    if not declared:
        return [], 0  # not an explicit-ID diagram; nothing to enforce
    fails, refs = [], 0
    for line in diagram.splitlines():
        a = ARROW_RE.match(line)
        if a:
            for end in a.groups():
                refs += 1
                if end not in declared:
                    fails.append(
                        f"FAIL: state-id '{end}' referenced in transition but not "
                        f"declared (declared: {sorted(declared - {'[*]'})})"
                    )
        c = CLASS_RE.match(line)
        if c:
            for target in (t.strip() for t in c.group(1).split(",")):
                refs += 1
                if target and target not in declared:
                    fails.append(
                        f"FAIL: state-id '{target}' in class statement not declared"
                    )
    return fails, refs


def check_cli(diagram):
    """Optional full-parse cross-check via mmdc. Fail-open when absent."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return [], (
            "INFO: mmdc not on PATH — skipped CLI parse cross-check "
            "(static checks stand alone)"
        )
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as f:
        f.write(diagram)
        src = f.name
    out = src + ".svg"
    try:
        proc = subprocess.run(
            [mmdc, "-i", src, "-o", out],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,  # non-zero is a finding, not an exception
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return [], f"INFO: mmdc invocation failed to run ({e}) — fail-open"
    if proc.returncode != 0:
        return [f"FAIL: mmdc parse error:\n{proc.stderr.strip()}"], None
    return [], "PASS: mmdc parsed the diagram without error"


def validate(text, run_cli=False):
    diagram = extract_mermaid(text)
    fails, notes = [], []

    cf, cp = check_contrast(diagram)
    fails += cf
    notes.append(
        f"contrast: {cp} pair(s) pass" if not cf else f"contrast: {len(cf)} FAIL"
    )

    sf, sr = check_state_ids(diagram)
    fails += sf
    notes.append(
        "state-ids: not an explicit-ID diagram (skipped)" if sr == 0 and not sf
        else f"state-ids: {sr} ref(s) checked"
    )

    if run_cli:
        clf, clnote = check_cli(diagram)
        fails += clf
        if clnote:
            notes.append(clnote)

    return fails, notes


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    run_cli = "--cli" in argv
    if not args or args[0] == "-":
        text = sys.stdin.read()
    else:
        with open(args[0]) as fh:
            text = fh.read()

    fails, notes = validate(text, run_cli=run_cli)
    for n in notes:
        print(n)
    for f in fails:
        print(f)
    if fails:
        print(f"\n{len(fails)} FAIL — Mermaid output is not render-safe.")
        return 1
    print("\nPASS: Mermaid output passed static render-safety checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
