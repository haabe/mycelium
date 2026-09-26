#!/usr/bin/env python3
"""A frozen prediction with no home, no expiry and no diff is an opinion with a date.

WHAT THIS GUARDS. `/mycelium:assumption-test` Step 5 tells the author to state a
prediction before running. Nothing tells them where it LANDS. Step 6's outputs are
"log in opportunities.yml" and "always update active.yml"; the instrument document
that actually carries the frozen prediction is written by nobody, governed by no
schema, and read by no check.

THE DOGFOOD EVIDENCE (roadmap repo, measured 2026-08-20):
  - 36 files in `.claude/evals/assumption-tests/`, of which 4 are metric adapter
    specs that drifted in because the directory has no membership rule.
  - 27 of them state a freeze convention IN PROSE, in 27 different phrasings:
    "PRE-REGISTERED 2026-08-16, BEFORE ANY FETCH", "Prediction was frozen before
    posting; nothing below the prediction was edited after", "Written and committed
    BEFORE the run". The author writes the contract by hand every time and never
    the same way twice, which is exactly why nothing can check it.
  - ZERO carry an expiry. Of the instruments carrying a prediction, the ones spot-
    checked by hand carry no date by which they must be scored.
  - Consequence, twice: an L0-adoption test held frozen thresholds for 102 days and
    was closed never-run; a 14-day pre-registration in another repo was never
    committed, so not even a git timestamp exists for it.

WHY THESE FOUR FIELDS AND NOT MORE. AsPredicted asks NINE questions, deliberately,
because its authors' stated design goal was to be "short and easy to read" and to
"include only what needs to be included". Length kills completion, and an unfinished
instrument protects nothing. Three of the four fields below are LIFTED from what the
corpus already writes by hand; only `score_by` is new, and it is the one whose
absence produced both failures above.

  type:          assumption-test        # membership. Without it, adapters drift in.
  frozen_at:     2026-08-16             # when
  frozen_before: "any comment is fetched"  # THE EVENT the freeze precedes
  score_by:      2026-08-30             # the expiry. The field nothing had.
  status:        live | scored | void | not-an-instrument

`frozen_before` is the corpus's own invention and it is better than a bare date.
A date does not establish precedence over the DATA; naming the contaminating event
does. "before posting", "before launching the subagent", "before any fetch".

THE FAILURE THIS IS REALLY FOR IS NOT FABRICATION, IT IS SILENT DRIFT. The COMPare
project checked 67 trials in the top five medical journals against their own
registered protocols: on average each reported 62% of its pre-specified outcomes and
silently ADDED 5.3 new ones; primary outcomes were correctly reported a mean 76% of
the time, ranging 25-96% by journal. Registries existed for every one of those
trials. What was missing was anybody diffing the registration against the report. So
this check's centre of gravity is DRIFT, not presence.

AMENDMENTS ARE RECORDED, NEVER FORBIDDEN, and that is the established practice rather
than a compromise. ClinicalTrials.gov keeps every revision in a public "History of
Changes" archive and never removes a registered record. Mature registries did not
solve the edit problem by preventing edits; they solved it by making every edit
permanently visible. Git gives a consumer the same property for free, which is the
only reason this check imports the remedy at all: the rule adopted for method
research in this framework is TAKE THE FAILURE MODES, LEAVE THE REMEDIES UNLESS THEY
ARE FREE.

WHAT THIS CHECK DOES NOT DO, STATED HERE AND PRINTED IN ITS OWN OUTPUT, because a
check whose green is misread is worse than no check. Preregistration does not make a
test severe. The methodological critique is blunt about it: treating a registration
as a signal of quality adds "a superficial veneer of rigor", and a preregistered
procedure that permits deviations is "a plan, not a prison" rather than a guarantee.
So this check CANNOT tell you the prediction was a good one, that the method fits the
question, that the sample means anything, or that the author did not simply write a
prediction soft enough to always hold. It checks four mechanical facts about a file.
Every green here is a green about paperwork.

Exit codes:
    0  every instrument carries a contract, nothing is due, nothing has drifted
    1  at least one instrument is uncontracted, undated, due/overdue, or drifted
    2  the check itself could not run

Python stdlib only, so it runs in any consumer regardless of environment.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

#: Where instruments live. A single directory, because a checker needs somewhere to
#: look and "wherever the session happened to be standing" is how a 102-day-old
#: frozen prediction goes unnoticed in an untracked scratch repo.
INSTRUMENT_DIR = Path(".claude") / "evals" / "assumption-tests"

#: Prose that means "there is a prediction in here". Deliberately WIDE: this set
#: decides whether a file WITHOUT a header gets reported as uncontracted, and the
#: expensive error is missing a real instrument, not flagging a stray document the
#: author then marks `not-an-instrument` once.
_PREDICTION_PROSE = re.compile(
    r"\b(frozen[ _]prediction|pre-?registered|i expect\b|i'?d be surprised if"
    r"|prediction[: ]|hypothesis[: ]|before the run|before any (?:data|fetch|response))",
    re.IGNORECASE,
)

#: The block whose later modification is the thing worth catching. Everything from a
#: prediction heading to the next heading of the same or higher level.
_FROZEN_BLOCK = re.compile(
    r"^(#{1,4})\s*[^\n]*\b(prediction|pre-?registration|frozen)\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)

_REQUIRED = ("type", "frozen_at", "frozen_before", "score_by", "status")
#: Fields required only on instruments frozen on or after a date (v0.209.0), so a new rule does
#: not fail a corpus written before it existed — the 0.195.0 shape (`different_builder` on
#: candidates surfaced on or after 2026-09-11). `does_not_reproduce`: one line naming the
#: conditions the test does NOT reproduce. The cheapest countermeasure the
#: subagent-simulation-misses-lived-friction cluster proposed in May, done voluntarily twice
#: in a fortnight and recorded nowhere; `mocked-persona-interview` already requires the
#: equivalent declaration for a simulated PERSON, and nothing asked it of a simulated RUN.
_REQUIRED_SINCE = {"does_not_reproduce": _dt.date(2026, 9, 15),
                   "decision_class": _dt.date(2026, 9, 27),
                   "test_weight": _dt.date(2026, 9, 27)}

#: A TEST SIZED TO THE DECISION IT INFORMS (v0.264.0). `decision_class` is how costly the
#: decision the test feeds is to get wrong (light: reversible, small opted-in audience, an
#: error caught before harm; heavy: hard to reverse, wide audience, money or safety);
#: `test_weight` is what the test costs to run. E2E runs 53-55 (a recipe page for five
#: opted-in testers) pre-registered a re-test needing twelve blind recipe lines and a
#: government nutrition dataset, and stalled three sessions on inputs the world could not
#: supply. A heavier test than its decision is allowed only by the founder, with the reason
#: written: `costly_test_reason` (>= 40 characters) and `costly_test_by: founder`.
_WEIGHTS = {"light": 0, "standard": 1, "heavy": 2}
_MIN_COSTLY_REASON_CHARS = 40

#: THE CLASS FROM THREE AXES (v0.269.0). One class carried three things (reversibility, reach and
#: harm), so three paying B2B clients (small, opted in, money) or ten households with a hardware
#: prototype (small, opted in, safety) fitted no class, and choosing "heavy" silenced OVERSIZED
#: (overfit audit, 2026-09-26). When the axes are recorded, the class is the heaviest of them and
#: a recorded class below it is MISCLASSED; a test lighter than its class is UNDERSIZED, overridden
#: the same way as a costly one, by the decision owner with a reason.
_AXES = {
    "decision_reversible": {"days": 0, "weeks": 1, "hard": 2},
    "decision_reach": {"opted_in": 0, "not_opted_in": 1, "everyone": 2},
    "decision_harm": {"none": 0, "money": 1, "health_or_safety": 2},
}

#: A live instrument gated on an EVENT rather than a date cannot honestly carry a
#: `score_by` — the data may never exist. It must still carry a `review_by`: the date
#: by which you decide whether to KEEP WAITING. Founder ruling 2026-08-20: "event gated
#: should have review dates. or even better - if it can trigger a review on/after the
#: event." The distinction is the point. A scoring date says data must exist by then; a
#: review date says a DECISION must exist by then, and a decision is always available.
#: Without it, "waiting on an event" is indistinguishable from "forgotten", which is how
#: one instrument here held frozen thresholds for 102 days and one for 104.
_VALID_STATUS = {"live", "scored", "void", "not-an-instrument"}
#: `runs_on` values that mean "an agent can run this now": data on disk, or public data it
#: can fetch. `human` (a send, a call, a ruling) is the third value and is never listed here.
_RUNNABLE = {"disk", "network"}
#: A runnable instrument older than this, still live, is a WARN in the report.
_RUNNABLE_WARN_DAYS = 14


def _parse_date(value: str | None) -> _dt.date | None:
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(str(value).strip().strip("\"'"))
    except (ValueError, TypeError):
        return None


def _frontmatter(text: str) -> dict[str, str] | None:
    """Parse a leading `---` block as flat key: value pairs.

    Hand-rolled rather than yaml.safe_load because this must run stdlib-only in any
    consumer. The header is flat by design, so a real parser buys nothing here.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    out: dict[str, str] = {}
    lines = text[3:end].splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        key, val = k.strip(), v.strip().strip("\"'")
        if val in (">-", ">", "|", "|-"):
            # FOLDED AND LITERAL BLOCKS. Without this the value parsed as the literal
            # ">-" and every continuation line was skipped for having no colon — so a
            # long field read as two characters, silently. Found 2026-08-27 when a
            # waiver reason written as a folded block failed a length check it passed
            # on inspection. Indentation-based, which is all a flat header needs.
            indent = len(line) - len(line.lstrip())
            parts = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                parts.append(nxt.strip())
                i += 1
            val = " ".join(p for p in parts if p)
        out[key] = val
    return out


def _strip_frontmatter(text: str) -> str:
    """Body only.

    FOUND BY DOGFOODING ON THE REAL CORPUS, 2026-08-20, and it made the flagship
    report untrustworthy on its first live run. A `#` comment inside the YAML
    header is not a markdown heading, but it looks exactly like one, and header
    comments on THESE files talk about predictions and freezing by definition. The
    first retrofitted instrument reported DRIFT against itself because the block
    finder matched a comment reading "# It held frozen thresholds for 102 days".
    A drift report that fires on the contract header would train its reader to
    ignore the one report this check exists for.
    """
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    return text if end == -1 else text[end + 4:]


def _frozen_block(text: str) -> str | None:
    """Return the prediction block, or None if no prediction heading is present."""
    text = _strip_frontmatter(text)
    m = _FROZEN_BLOCK.search(text)
    if not m:
        return None
    level = len(m.group(1))
    rest = text[m.end():]
    nxt = re.search(rf"^#{{1,{level}}}\s", rest, re.MULTILINE)
    return rest[: nxt.start()] if nxt else rest


def _git_original(root: Path, path: Path) -> tuple[str | None, str | None]:
    """The file's content at the commit that introduced it, plus that commit's sha.

    Returns (None, None) when git cannot answer — not tracked, no git, shallow
    clone. THAT IS NOT A PASS and callers must not treat it as one: an untracked
    instrument is the habisji failure exactly, and it is reported in its own right.
    """
    try:
        rel = str(path.relative_to(root))
        sha = subprocess.run(
            ["git", "-C", str(root), "log", "--follow", "--diff-filter=A",
             "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout.strip().splitlines()
        if not sha:
            return None, None
        first = sha[-1]
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"{first}:{rel}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if blob.returncode != 0:
            return None, None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, None
    else:
        return blob.stdout, first


def _anchor_block(root: Path, ref: str) -> str | None:
    """The text of a `file#key` anchor under .claude/canvas/, or None.

    Deliberately NOT a YAML parse: this script is stdlib-only so it runs in any
    consumer, and PyYAML is not stdlib. It finds the first line whose stripped form
    starts with `key:` and takes everything until a line indented at or below it —
    the same block-boundary technique used for markdown prediction blocks.
    """
    if "#" not in ref:
        return None
    fname, _, key = ref.partition("#")
    key = key.strip().split(".")[-1]
    path = root / ".claude" / "canvas" / fname.strip()
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}:"):
            indent = len(line) - len(line.lstrip())
            out = [line]
            for nxt in lines[i + 1:]:
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                out.append(nxt)
            return "\n".join(out)
    return None


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


_MALFORMED = object()   # "there IS a date and it is garbage" — not the same as absent


def _scoring_date(name: str, fm: dict[str, str], res: dict):
    """The score_by date, None if absent, or _MALFORMED if present and unparseable.

    A MALFORMED DATE IS NOT A MISSING ONE. Both used to take the no-scoring-date
    path, so an instrument carrying `score_by: 2026-13-45` was reported as having
    no scoring date — true of the parse, false of the file, and it sends the reader
    looking for a promise that is already written down.
    """
    raw = fm.get("score_by")
    parsed = _parse_date(raw)
    if raw and parsed is None:
        res["undated"].append(f"{name} (score_by is not an ISO date: {raw!r})")
        return _MALFORMED
    return parsed


_MIN_WAIVER_REASON_CHARS = 20


def _required_field_state(fm: dict[str, str]) -> tuple[list[str], list[tuple[str, str]]]:
    """Split empty required fields into UNFILLED and DELIBERATELY EMPTY.

    THE CHECK USED TO REPORT A DECISION AS A DEFECT, PERMANENTLY. Four instruments in
    the dogfood corpus carry an empty `frozen_before` **on purpose**, each with the
    reason written in a comment above it: *"DELIBERATELY EMPTY. This file states no
    freeze event, and inventing a plausible one is exactly the failure that made a bulk
    retrofit unsafe."* Three are additionally VOID — an agent-as-instrument that never
    self-logged has no data to score and no freeze event to name.

    The correct state could never satisfy the check, so every run carried four entries
    meaning "working as intended", and **the next genuine INCOMPLETE would arrive in a
    list already mostly noise.** A permanent unfixable warning trains the reader to skip
    the report.

    THE FIELD ITSELF STAYS EMPTY, WHICH IS THE POINT. The waiver goes in a SIBLING key,
    `<field>_absent_reason`, so nothing writes a fabricated freeze event into
    `frozen_before` — the founder's 2026-08-20 ruling on those files was "leave empty,
    the silence is the finding", and a sentinel VALUE would violate its letter while
    honouring its spirit. This records the reason that was already written, in a key a
    reader can grep, next to the emptiness it explains.

    A WAIVER IS NOT FREE AND IS NOT SILENT. The reason must be substantive
    (>= 20 characters, so `x` or `n/a` does not buy an exemption), and waived fields are
    REPORTED in their own section rather than suppressed — an exemption nobody sees is
    how the next one gets granted without argument.
    """
    missing: list[str] = []
    waived: list[tuple[str, str]] = []
    frozen = _parse_date(fm.get("frozen_at"))
    dated = [k for k, since in _REQUIRED_SINCE.items() if frozen is not None and frozen >= since]
    for k in (*_REQUIRED, *dated):
        if k == "score_by" or fm.get(k):
            continue
        reason = str(fm.get(f"{k}_absent_reason", "") or "").strip()
        if len(reason) >= _MIN_WAIVER_REASON_CHARS:
            waived.append((k, reason))
        else:
            missing.append(k)
    return missing, waived


def _expiry(name: str, fm: dict[str, str], today: _dt.date, res: dict, root: Path) -> None:
    """Scoring date, review date, and the event trigger — in that order of preference."""
    status = fm.get("status")
    due = _scoring_date(name, fm, res)
    if due is _MALFORMED:
        return
    if due is not None:
        if status == "live" and due < today:
            res["due"].append((name, str(due), (today - due).days))
        return

    # No scoring date. For a live instrument that is only legitimate with a REVIEW date,
    # which is a promise about a decision rather than about data.
    if status != "live":
        res["undated"].append(name)
        return

    review = _parse_date(fm.get("review_by"))
    if review is None:
        res["no_review"].append(name)
    elif review < today:
        res["review_due"].append(
            (name, f"review date {review} passed {(today - review).days} days ago"))

    _review_trigger(name, fm, res, root)


def _review_trigger(name: str, fm: dict[str, str], res: dict, root: Path) -> None:
    """The optional event-anchored half of the review promise.

    Extracted from `_expiry` 2026-08-26: it answers a different question (has the
    EVENT happened) from the dates above it (has the DATE passed).
    """
    # THE TRIGGER HALF. It fires on the event rather than on a calendar, WHICH IS BETTER
    # ONLY WHERE THE EVENT IS ACTUALLY RECORDED SOMEWHERE.
    #
    # "HOW CAN WE KNOW WHETHER AN EVENT HAS HAPPENED IF WE DON'T TRACK THEM?" — the founder,
    # 2026-08-20, and it is the right question to ask of this code. THE ANSWER IS THAT THIS
    # DOES NOT TRACK EVENTS. It detects CHANGE at an anchor you nominate, and infers the
    # event from the trace. Three consequences, all of them limits:
    #
    #   1. A rewording of the anchor fires it too. Deliberate: a spurious review costs one
    #      glance, a missed event costs months, and this corpus holds instruments that sat
    #      102 and 104 days to prove which cost is real.
    #   2. IT INHERITS THE DISCIPLINE IT IS MEANT TO BACKSTOP. If nobody records the event,
    #      the anchor never changes and the trigger never fires. Pointing `review_on` at a
    #      PROSE SUMMARY is the weak form and close to circular — the summary only updates
    #      when someone already noticed.
    #   3. So POINT IT AT AN EVENT LOG, not at a conclusion. In a Mycelium project the
    #      surfaces that actually record events are `human-tasks.yml` touch_log entries
    #      (191 dated entries over 102 days in the dogfood repo, a discipline that
    #      demonstrably holds), a new task id, and git history on any canvas file. Those
    #      are written AS the event happens. A confidence field or a density summary is
    #      written after someone has drawn a conclusion, which is later and rarer.
    #
    # AND WHERE THE EVENT IS RECORDED NOWHERE, THERE IS NO TRIGGER TO BUILD. That case is
    # exactly why `review_by` is required and this is optional: a date promises a DECISION,
    # which is always available, where a trigger promises DETECTION, which is not.
    ref = fm.get("review_on")
    if not ref:
        return
    block = _anchor_block(root, ref)
    if block is None:
        res["bad_anchor"].append((name, ref))
        return
    recorded = fm.get("review_on_fingerprint", "")
    now = _fingerprint(block)
    if not recorded:
        res["bad_anchor"].append((name, f"{ref} (no fingerprint recorded; current is {now})"))
    elif recorded != now:
        res["review_due"].append(
            (name, f"{ref} CHANGED since the freeze — the event may have occurred"))


def _drift(path: Path, root: Path, text: str, fm: dict[str, str], res: dict) -> None:
    """Did the prediction block change after the commit that introduced it?

    An untracked file is reported in its own right rather than as a pass: nothing
    timestamps it, so nothing distinguishes written-before from written-after.
    """
    original, sha = _git_original(root, path)
    if original is None:
        res["untracked"].append(path.name)
        return
    if fm.get("amended"):
        return  # recorded amendments are legitimate; silent ones are the finding
    was, now = _frozen_block(original), _frozen_block(text)
    if was is not None and now is not None and was.strip() != now.strip():
        res["drifted"].append((path.name, sha[:8] if sha else "?"))


def _proportion(name: str, fm: dict[str, str], res: dict) -> None:
    """Whether the test is sized to its decision (v0.264.0). An unknown class or weight is
    reported; a heavier test than its decision is OVERSIZED unless the founder overrode it with a
    written reason, which is then printed beside the report, never hidden."""
    cls = str(fm.get("decision_class", "") or "").strip().lower()
    weight = str(fm.get("test_weight", "") or "").strip().lower()
    if not cls or not weight:
        return  # a missing field is INCOMPLETE, reported by _required_field_state
    bad = [f"{k}: {v!r}" for k, v in (("decision_class", cls), ("test_weight", weight))
           if v not in _WEIGHTS]
    if bad:
        res["bad_proportion"].append((name, ", ".join(bad)))
        return
    derived = _derived_class(fm, name, res)
    if derived is not None and _WEIGHTS[cls] < _WEIGHTS[derived]:
        res["misclassed"].append((name, f"decision_class {cls}, and its axes make it {derived}"))
        cls = derived
    if _WEIGHTS[weight] == _WEIGHTS[cls]:
        return
    key, bucket = ("costly", "oversized") if _WEIGHTS[weight] > _WEIGHTS[cls] \
        else ("light", "undersized")
    reason = str(fm.get(f"{key}_test_reason", "") or "").strip()
    by = str(fm.get(f"{key}_test_by", "") or "").strip().lower()
    if len(reason) >= _MIN_COSTLY_REASON_CHARS and by and by != "agent":
        res["costly_override"].append((name, f"{weight} test, {cls} decision", by, reason))
    else:
        res[bucket].append((name, f"{weight} test for a {cls} decision"))


def _derived_class(fm: dict[str, str], name: str, res: dict) -> str | None:
    """The heaviest of the recorded decision axes, or None when none is recorded (v0.269.0)."""
    levels = []
    for axis, scale in _AXES.items():
        v = str(fm.get(axis, "") or "").strip().lower()
        if not v:
            continue
        if v not in scale:
            res["bad_proportion"].append((name, f"{axis}: {v!r}"))
            return None
        levels.append(scale[v])
    if not levels:
        return None
    return {n: k for k, n in _WEIGHTS.items()}[max(levels)]


def _classify(path: Path, root: Path, today: _dt.date, res: dict) -> None:
    """Route one file into the report buckets."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = _frontmatter(text) or {}

    if fm.get("type") != "assumption-test":
        # No contract. Only a problem if it READS like an instrument — this is what
        # keeps metric-adapter specs from being reported forever in a directory
        # that has no membership rule.
        if _PREDICTION_PROSE.search(text):
            res["uncontracted"].append(path.name)
        return

    status = fm.get("status", "")
    if status not in _VALID_STATUS:
        res["bad_status"].append((path.name, status or "(missing)"))
        return
    if status == "not-an-instrument":
        return

    res["contracted"].append(path.name)

    # EVERY required field, not just the expiry. FOUND 2026-08-20 while retrofitting a
    # real corpus: _REQUIRED listed five fields and only score_by was ever acted on, so a
    # header with an empty `frozen_before` passed GREEN. That is the interface failure
    # this check exists to prevent, sitting inside the check -- an agent greps
    # frozen_before, gets nothing, and cannot establish that the prediction preceded the
    # data. A required field nothing enforces is a suggestion.
    missing, waived = _required_field_state(fm)
    if missing:
        res["incomplete"].append((path.name, ", ".join(missing)))
    for field, why in waived:
        res["waived"].append((path.name, field, why))

    _proportion(path.name, fm, res)
    _expiry(path.name, fm, today, res, root)

    # RUNNABLE, NEVER RUN (v0.183.0). A live instrument whose `runs_on` is `disk` or `network`
    # needs no human and no new data; every day it stays live it reads as "pending" to a
    # reader who cannot tell it from one that waits on a send. Measured on the dogfood
    # record 2026-09-09: a zero-build retrodiction designed 2026-06-12 ran 89 days later, in
    # an hour, once someone asked "why wait?". Reported beside the problems, never counted
    # as one: the run is what should be automatic, the reading stays pre-registered.
    if status == "live" and fm.get("runs_on", "").strip().lower() in _RUNNABLE:
        frozen = _parse_date(fm.get("frozen_at"))
        age = (today - frozen).days if frozen else None
        res["runnable"].append((path.name, fm["runs_on"].strip().lower(), age))

    if status == "scored":
        res["scored"].append(path.name)
        if re.search(r"\b(refuted|falsifi|missed|did not hold|void)\b", text, re.IGNORECASE):
            res["refuted"].append(path.name)

    _drift(path, root, text, fm, res)


def analyse(root: Path, today: _dt.date) -> dict:
    d = root / INSTRUMENT_DIR
    res: dict[str, list] = {
        "uncontracted": [], "undated": [], "due": [], "drifted": [],
        "untracked": [], "bad_status": [], "contracted": [], "scored": [],
        "refuted": [], "incomplete": [], "waived": [], "no_review": [], "review_due": [],
        "bad_anchor": [], "runnable": [], "oversized": [], "costly_override": [],
        "bad_proportion": [], "undersized": [], "misclassed": [],
    }
    for path in sorted(d.glob("*.md")):
        _classify(path, root, today, res)
    return res


def _emit_proportion(r: dict, emit) -> None:
    """OVERSIZED and BAD SIZE count as problems; a founder override is printed, never counted
    (v0.264.0)."""
    emit(r["oversized"],
         "OVERSIZED — the test costs more than the decision it informs (v0.264.0). Choose a "
         "lighter test, or have the decision owner override it with `costly_test_reason` "
         "(why the heavier test is worth it) and `costly_test_by` (their role: founder, product "
         "lead, team).",
         lambda t: f"{t[0]}: {t[1]}")
    emit(r["undersized"],
         "UNDERSIZED — the test is lighter than the decision it informs (v0.269.0). Choose a "
         "heavier test, or have the decision owner accept it with `light_test_reason` and "
         "`light_test_by` (their role).",
         lambda t: f"{t[0]}: {t[1]}")
    emit(r["misclassed"],
         "MISCLASSED — decision_class is lighter than its recorded axes (v0.269.0).",
         lambda t: f"{t[0]}: {t[1]}")
    emit(r["bad_proportion"],
         "BAD SIZE — decision_class and test_weight are light | standard | heavy.",
         lambda t: f"{t[0]}: {t[1]}")
    # NOT via emit(): an override is a recorded founder decision, not a problem. Printed so
    # it stays visible, the way waivers are.
    if r["costly_override"]:
        print("\nSIZED BY CHOICE — a test heavier or lighter than its decision, accepted by "
              "its decision owner with a reason.")
        for name, size, by, why in r["costly_override"]:
            print(f"  {name} ({size}, by {by}): {why}")


def _emit_runnable(r: dict) -> None:
    """RUNNABLE NOW, NEVER RUN: a to-do, not a defect. Printed among the advisories and never
    counted, because it names work an agent can do in this session without asking anyone."""
    if not r["runnable"]:
        return
    print("\nRUNNABLE NOW, NEVER RUN — live, and `runs_on` says disk or network: no human "
          "and no new data needed. Run the oldest in this session, or give it a dated "
          "score_by and say why not now. Oldest first.")
    undated = 10**6
    for name, how, age in sorted(r["runnable"], key=lambda t: -(t[2] if t[2] is not None else
    undated)):
        flag = "  WARN" if age is not None and age > _RUNNABLE_WARN_DAYS else ""
        shown = age if age is not None else "?"
        print(f"  {name} (runs_on {how}, {shown} days live){flag}")


CANVAS_DIR = Path(".claude") / "canvas"
SCORED_KEYS = ("prediction_scored", "scored", "scored_at", "score", "outcome")
_CANVAS_WALK_DEPTH = 12


_CLOSED_STATUS = ("completed", "closed", "done", "cancelled")


def _has_score(node: dict) -> bool:
    """A score is an exact SCORED_KEYS name, `outcome_scored`, or any key that STARTS with `scored`.

    v0.226.3. Read by hand on the dogfood canvas 2026-09-17: eleven of eleven DUE lines were
    already scored, under `scored_at_horizon`, `scored_2026_08_18`, `outcome_scored`,
    `SCORED_2026_08_25_...`. The prefix is `scored` and never `score` or `outcome`: the dangerous
    direction is hiding an unscored prediction, and `score_by` is a date, `outcome_classes` a plan.
    """
    for k in node:
        low = str(k).lower()
        if low in SCORED_KEYS or low == "outcome_scored" or low.startswith("scored"):
            return True
    return False


def _classify_canvas_prediction(node: dict, canvas: str, today: _dt.date, res: dict) -> None:
    label = f"{canvas}#{node.get('id', '?')}"
    horizon = _parse_date(str(node.get("horizon") or node.get("score_by") or ""))
    if _has_score(node):
        res["scored"].append(label)
    elif horizon is None:
        res["undated"].append(label)
    elif horizon < today and str(node.get("status") or "").lower() in _CLOSED_STATUS:
        res["closed_unscored"].append((label, str(horizon)))
    elif horizon < today:
        res["due"].append((label, str(horizon), (today - horizon).days))
    else:
        res["live"].append((label, str(horizon)))


def canvas_predictions(root: Path, today: _dt.date) -> dict[str, list]:
    """Frozen predictions that live in canvas files, outside the instruments directory.

    v0.207.0. This check scanned `.claude/evals/assumption-tests/` and nothing else, so on
    2026-09-03 it reported "problems: 0" while `human-tasks.yml#ht-060` carried a prediction
    frozen 2026-08-02 with a horizon one day past. What noticed was the task-staleness
    rule, which called it "untouched 32d" and offered to nudge a contact the task's own
    `do_not` forbade nudging. A prediction beside a horizon is the same object this check
    governs wherever it lives. Reported, never required to move: a prediction separated
    from the task it is about is the one that goes unscored.

    Scored is inferred from any of SCORED_KEYS on the same node; a task closed with no
    such key and a passed horizon is DUE, and that is the finding the staleness rule
    pointed at the wrong remedy.
    """
    res: dict[str, list] = {"due": [], "live": [], "scored": [], "undated": [],
                            "closed_unscored": []}
    cdir = root / CANVAS_DIR
    if not cdir.is_dir():
        return res
    for path in sorted(cdir.glob("*.yml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue  # parse failures belong to validate_canvas
        _walk_canvas_predictions(doc, path.stem, today, res)
    return res


def _walk_canvas_predictions(node, canvas: str, today: _dt.date, res: dict, depth: int = 0):
    if depth > _CANVAS_WALK_DEPTH:
        return
    if isinstance(node, dict):
        if "frozen_prediction" in node:
            _classify_canvas_prediction(node, canvas, today, res)
        for v in node.values():
            _walk_canvas_predictions(v, canvas, today, res, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _walk_canvas_predictions(v, canvas, today, res, depth + 1)


def _emit_canvas_predictions(cp: dict[str, list]) -> None:
    total = sum(len(v) for v in cp.values())
    if not total:
        return
    print(f"\nPREDICTIONS IN THE CANVAS, OUTSIDE THE CONTRACT — {total}: {len(cp['due'])} due "
          f"for scoring, {len(cp['live'])} live, {len(cp['scored'])} scored, "
          f"{len(cp['undated'])} with no horizon, {len(cp['closed_unscored'])} closed with no "
          f"score found. Not counted as problems and not asked to "
          f"move: a prediction beside the task it is about is where it gets scored.")
    for label, when, days in cp["due"]:
        print(f"  DUE     {label} (horizon {when}, {days} days ago) — score it; this is not "
              f"a stale task and the remedy is not a nudge")
    for label, when in cp["closed_unscored"]:
        print(f"  CLOSED  {label} (horizon {when}) — the task is closed and no score was found "
              f"under a known key; if it was scored in prose or under another name, add "
              f"`prediction_scored:` pointing at it. Not called DUE: nothing here is overdue work")
    for label in cp["undated"]:
        print(f"  UNDATED {label} — a prediction with no horizon can never be overdue")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the instrument output contract.")
    ap.add_argument("--root", default=".", help="project root containing .claude/")
    ap.add_argument("--today", default=None, help="ISO date override (testing)")
    args = ap.parse_args(argv)

    # tz-aware: a due-date check on local time disagrees with itself across
    # machines, and the disagreement shows up as overdue-here-not-there.
    today = _parse_date(args.today) if args.today else _dt.datetime.now(tz=_dt.UTC).date()
    if today is None:
        print("UNKNOWN: --today is not an ISO date", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not (root / INSTRUMENT_DIR).is_dir():
        # UNKNOWN, never clean. A check that cannot run must not report a pass.
        print(f"UNKNOWN: no {INSTRUMENT_DIR} under {root}", file=sys.stderr)
        return 2

    r = analyse(root, today)
    problems = 0

    def emit(items, head, fmt=str):
        nonlocal problems
        if not items:
            return
        problems += len(items)
        print(f"\n{head}")
        for it in items:
            print("  " + fmt(it))

    emit(r["uncontracted"],
         "UNCONTRACTED — reads like an instrument, carries no contract header. "
         "Add one, or mark `status: not-an-instrument` so it stops being asked about.")
    emit(r["undated"],
         "NO EXPIRY — a prediction with no score_by can never be overdue, so it can "
         "never be scored, so it is free to be right forever.")
    emit(r["incomplete"],
         "INCOMPLETE — a contract field is present but empty. A required field nothing "
         "enforces is a suggestion, and an agent grepping it gets silence rather than an "
         "answer.",
         lambda t: f"{t[0]} (empty: {t[1]})")
    # NOT via emit(): a waiver is not a problem and must not move the exit code.
    # It is still PRINTED, because an exemption nobody sees is how the next one gets
    # granted without argument.
    if r["waived"]:
        print("\nWAIVED — a required field is empty and the file says why, in "
              "`<field>_absent_reason`. NOT a pass and NOT a defect: it is a recorded "
              "decision that the honest value is no value. Read the reasons; a waiver "
              "that stops being true is invisible from here.")
        for name, field, why in r["waived"]:
            print(f"  {name} ({field}): {why}")

    emit(r["no_review"],
         "NO REVIEW DATE — live, gated on an event, and carrying no review_by. A scoring "
         "date promises DATA by a date, which an event-gated test cannot promise. A review "
         'date promises a DECISION by a date, which is always available. Without one, '
         '"waiting" and "forgotten" look identical.')
    emit(r["review_due"], "REVIEW DUE — decide whether to keep waiting.",
         lambda t: f"{t[0]}: {t[1]}")
    emit(r["bad_anchor"],
         "REVIEW ANCHOR UNUSABLE — review_on names something that cannot be read, or has "
         "no fingerprint to compare against. An unreadable trigger is a trigger that never "
         "fires, which is worse than no trigger because it looks like one.",
         lambda t: f"{t[0]}: {t[1]}")
    emit(r["due"], "DUE / OVERDUE — status is live and score_by has passed.",
         lambda t: f"{t[0]} (due {t[1]}, {t[2]} days ago)")
    emit(r["drifted"],
         "DRIFTED — the prediction block changed after the commit that introduced it, "
         "and no `amended:` note explains it. This is outcome switching: the failure "
         "COMPare found in 67 registered trials, where the registry existed and "
         "nobody diffed it.",
         lambda t: f"{t[0]} (introduced {t[1]})")
    emit(r["untracked"],
         "NOT IN GIT — nothing timestamps this prediction, so nothing distinguishes "
         "written-before from written-after.")
    emit(r["bad_status"], "BAD STATUS — must be live | scored | void | not-an-instrument.",
         lambda t: f"{t[0]}: {t[1]}")
    _emit_proportion(r, emit)

    _emit_runnable(r)
    _emit_canvas_predictions(canvas_predictions(root, today))

    n = len(r["contracted"])
    if r["scored"] and not r["refuted"]:
        # Advisory, never an error. A young corpus legitimately has few scores.
        print(f"\nNOTE: {len(r['scored'])} scored instrument(s) and none records a "
              "refutation. A record that has never been wrong was not at risk. Not an "
              "error, and worth asking whether the predictions are soft.")

    print(f"\ninstruments under contract: {n}; scored: {len(r['scored'])}; "
          f"problems: {problems}")
    print("WHAT A GREEN MEANS: the contract fields parse and agree with git. That is an "
          "INTERFACE check, not paperwork — the header is how a later agent finds a frozen "
          "prediction, tells live from scored, and knows the block was written before the "
          "data. A malformed header does not mislead a human, who skims past it; it makes "
          "an agent grepping `status: live` conclude there are no live instruments.")
    print("WHAT A GREEN DOES NOT MEAN: that the prediction was good, that the method fits "
          "the question, or that the test was severe. Preregistration adds no severity on "
          "its own, and reading a green here as a quality signal is the veneer-of-rigor "
          "failure.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
