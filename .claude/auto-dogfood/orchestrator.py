#!/usr/bin/env python3
"""
Mycelium Auto-Dogfood Orchestrator

Runs full-session dogfood scenarios by alternating between a Mycelium Agent
and a User Simulator agent. Each scenario runs in an isolated working
directory with a fresh Mycelium template.

Usage:
    python orchestrator.py run scenarios/sw-cli-solo-value-risk.yml
    python orchestrator.py run-all scenarios/
    python orchestrator.py report results/
    python orchestrator.py compare results/baseline.json results/variant.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

from lib.evaluator import Evaluator
from lib.prompts import SKILL_OUTPUTS, build_mycelium_prompt, build_user_prompt
from lib.runner import ClaudeRunner
from lib.scenario import Scenario


MYCELIUM_TEMPLATE = Path(
    os.environ.get(
        "MYCELIUM_TEMPLATE",
        Path(__file__).resolve().parent.parent.parent,  # .claude/auto-dogfood -> .claude -> repo root
    )
)

# Files and directories to copy into the isolated workdir
TEMPLATE_ITEMS = [
    "CLAUDE.md",
    ".claude",
]


class DogfoodSession:
    """Manages a single dogfood scenario execution."""

    def __init__(self, scenario: Scenario, verbose: bool = False):
        self.scenario = scenario
        self.verbose = verbose
        self.workdir: Path | None = None
        self.runner: ClaudeRunner | None = None
        self.observations: list[dict] = []
        self.prompt_sizes: list[int] = []
        self.round = 0
        self.start_time: float = 0
        self._prev_decision_log_entries = 0

    def setup(self) -> Path:
        """Create isolated working directory with fresh Mycelium template."""
        workdir = Path(tempfile.mkdtemp(prefix="mycelium-dogfood-"))

        for item in TEMPLATE_ITEMS:
            src = MYCELIUM_TEMPLATE / item
            dst = workdir / item
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif src.is_file():
                shutil.copy2(src, dst)

        # Clean project-specific state from the template
        for state_path in [
            workdir / ".claude" / "diamonds" / "active.yml",
            workdir / ".claude" / "state",
            workdir / ".claude" / "harness" / "decision-log.md",
        ]:
            if state_path.is_dir():
                shutil.rmtree(state_path)
                state_path.mkdir(parents=True)
            elif state_path.is_file():
                state_path.write_text(self._empty_template(state_path.name))

        # Ensure files the agent READS exist (corrections, patterns, guardrails)
        for stub_path, stub_content in [
            (workdir / ".claude" / "memory" / "corrections.md",
             "# Corrections\n\nNo corrections logged yet.\n"),
            (workdir / ".claude" / "memory" / "patterns.md",
             "# Patterns\n\nNo patterns logged yet.\n"),
        ]:
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            if not stub_path.exists():
                stub_path.write_text(stub_content)

        # Claude Code has hardcoded write protection on .claude/ paths —
        # no settings or flags can override it. In interactive mode, users
        # approve writes manually. In headless -p mode, there's no human.
        #
        # Solution: move writable dirs to top-level and symlink back.
        # The agent writes to canvas/, diamonds/, harness/ (no .claude/ prefix).
        # Symlinks ensure the framework's hooks and CLAUDE.md references to
        # .claude/canvas/ etc. still resolve correctly.
        for dirname in ["canvas", "diamonds", "harness"]:
            dot_path = workdir / ".claude" / dirname
            top_path = workdir / dirname

            # Move contents to top-level
            if dot_path.is_dir() and not dot_path.is_symlink():
                if top_path.exists():
                    shutil.rmtree(top_path)
                shutil.move(str(dot_path), str(top_path))
            elif not top_path.exists():
                top_path.mkdir(parents=True)

            # Symlink .claude/X -> X so framework references still work
            if dot_path.exists() or dot_path.is_symlink():
                dot_path.unlink() if dot_path.is_symlink() else shutil.rmtree(dot_path)
            dot_path.symlink_to(os.path.relpath(top_path, dot_path.parent))

        # Clean canvas files so agent creates fresh (not overwrites)
        canvas_dir = workdir / "canvas"
        for yml in canvas_dir.glob("*.yml"):
            yml.unlink()

        # Clean write targets so agent creates them fresh
        for target in [
            workdir / "harness" / "decision-log.md",
            workdir / "diamonds" / "active.yml",
        ]:
            if target.exists():
                target.unlink()

        # Write initial_state files if scenario provides pre-populated state
        if self.scenario.initial_state:
            for rel_path, content in self.scenario.initial_state.items():
                target = workdir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)

        # Snapshot initial diamond phases for diamond_not_advanced evaluator
        active_path = workdir / "diamonds" / "active.yml"
        if active_path.exists():
            try:
                active_data = yaml.safe_load(active_path.read_text()) or {}
                initial_phases = {}
                for d in active_data.get("active_diamonds", []):
                    if d.get("id"):
                        initial_phases[d["id"]] = d.get("phase", "discover")
                phases_file = workdir / "diamonds" / "initial_phases.yml"
                phases_file.write_text(yaml.dump(initial_phases))
            except Exception:
                pass

        # Keep the REAL settings.json and CLAUDE.md — the dogfood must test
        # the actual framework, not a stripped-down version. The test harness
        # must work within the framework's constraints (hooks, permissions,
        # mandatory pre-task protocol). If the agent struggles, that's a
        # finding about the framework, not something to work around.

        # Init git so tools work correctly
        subprocess.run(
            ["git", "init"], cwd=workdir, capture_output=True, check=True,
        )
        # Set local git identity for the temp repo (CI may lack global config)
        subprocess.run(
            ["git", "config", "user.email", "dogfood@mycelium.local"],
            cwd=workdir, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Mycelium Dogfood"],
            cwd=workdir, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "add", "."], cwd=workdir, capture_output=True, check=True,
        )
        result = subprocess.run(
            ["git", "commit", "-m", "Initialize Mycelium template for dogfood"],
            cwd=workdir, capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git commit failed in {workdir}:\n"
                f"stdout: {result.stdout[:500]}\n"
                f"stderr: {result.stderr[:500]}"
            )

        self.workdir = workdir
        self.runner = ClaudeRunner(workdir)
        return workdir

    def run(self) -> dict:
        """Execute the full dogfood scenario and return results."""
        if not self.workdir:
            self.setup()

        self.start_time = time.monotonic()
        self._log(f"Starting scenario: {self.scenario.name}")
        self._log(f"Workdir: {self.workdir}")

        early_exit = False
        for step in self.scenario.journey:
            if self._budget_exceeded() or early_exit:
                if early_exit:
                    self._log("All criteria met, stopping early.")
                else:
                    self._log("Budget exceeded, stopping.")
                break

            self._log(f"Step: /{step.skill} (rounds={step.rounds})")
            planted = None
            if step.planted_failure:
                planted = self.scenario.get_failure_for_skill(step.skill)

            for r in range(step.rounds):
                self.round += 1
                self._run_round(step.skill, planted_failure=planted)

            # Check if all criteria already pass — exit early to save tokens
            if self.round >= 2:  # Need at least 2 rounds for meaningful check
                mid_evaluator = Evaluator(self.workdir)
                mid_result = mid_evaluator.evaluate(self.scenario.success_criteria)
                if mid_result["score"] >= 1.0:
                    early_exit = True

        # Final evaluation
        evaluator = Evaluator(self.workdir)
        eval_result = evaluator.evaluate(self.scenario.success_criteria)

        elapsed = round(time.monotonic() - self.start_time, 1)
        self._log(
            f"Done. Score: {eval_result['score']:.0%} "
            f"({len(eval_result['passed'])}/{len(eval_result['passed']) + len(eval_result['failed'])})"
        )

        proposals = self._generate_proposals(eval_result)
        if proposals:
            self._log(f"Proposals: {len(proposals)} surface edit(s) suggested")

        return {
            "scenario": self.scenario.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": eval_result["score"] >= 0.8,
            "score": round(eval_result["score"], 3),
            "criteria": {
                "passed": eval_result["passed"],
                "failed": eval_result["failed"],
            },
            "rounds_used": self.round,
            "time_seconds": elapsed,
            "token_usage": self.runner.token_tracker.to_dict() if self.runner else {},
            "observations": self.observations,
            "proposals": proposals,
            "workdir": str(self.workdir),
        }

    # Max agentic turns per skill type.
    # The framework's mandatory pre-task protocol (CLAUDE.md) requires the
    # agent to read corrections.md, guardrails.md, identify diamond, and
    # load domain context. This costs ~5-8 turns before actual work begins.
    # Budget accordingly — these limits must accommodate real framework overhead.
    SKILL_MAX_TURNS = {
        "interview": 25,
        "mocked-persona-interview": 25,
        "diamond-assess": 20,
        "diamond-progress": 20,
        "ost-builder": 20,
        "ice-score": 15,
        "assumption-test": 15,
        "delivery-bootstrap": 25,
        "reflexion": 30,
        "dora-check": 15,
        "retrospective": 15,
        "wardley-map": 20,
        "team-shape": 15,
        "jtbd-map": 15,
        "launch-tier": 15,
        "service-check": 15,
        "bias-check": 15,
        "privacy-check": 15,
        "regulatory-review": 15,
        "security-review": 15,
        "cynefin-classify": 10,
        "bvssh-check": 15,
        "definition-of-done": 15,
        "corrections-audit": 15,
    }

    SKILL_TIMEOUTS = {
        "interview": 300,
        "mocked-persona-interview": 400,
        "diamond-assess": 120,
        "diamond-progress": 180,
        "ost-builder": 240,
        "ice-score": 120,
        "assumption-test": 180,
        "delivery-bootstrap": 300,
        "reflexion": 600,
        "dora-check": 120,
        "retrospective": 180,
        "wardley-map": 180,
        "team-shape": 120,
        "jtbd-map": 120,
        "launch-tier": 120,
        "service-check": 120,
        "bias-check": 120,
        "privacy-check": 120,
        "regulatory-review": 120,
        "security-review": 120,
        "cynefin-classify": 90,
        "bvssh-check": 120,
        "definition-of-done": 120,
        "corrections-audit": 120,
    }

    def _run_round(
        self,
        skill: str,
        planted_failure=None,
    ):
        """Execute one orchestrator round.

        For interview skills: agent asks questions -> user sim responds -> agent synthesizes.
        For all other skills: single agent call with pre-loaded context (no reads needed).
        """
        max_turns = self.SKILL_MAX_TURNS.get(skill, 10)
        timeout = self.SKILL_TIMEOUTS.get(skill, 300)

        if skill in ("interview",) and not planted_failure:
            # Interview: agent asks, user responds, then synthesize
            mycelium_prompt = build_mycelium_prompt(
                self.scenario, skill, workdir=self.workdir,
            )
            self.prompt_sizes.append(len(mycelium_prompt))
            mycelium_result = self.runner.run(
                mycelium_prompt,
                model=self.scenario.model_mycelium,
                timeout=timeout,
                role="mycelium",
                max_turns=max_turns,
            )
            self._log(f"  Mycelium agent: {len(mycelium_result.stdout)} chars, "
                       f"{mycelium_result.duration_seconds}s")

            # User simulator responds to agent questions
            if mycelium_result.stdout:
                user_prompt = build_user_prompt(
                    self.scenario, skill, mycelium_result.stdout,
                )
                user_result = self.runner.run(
                    user_prompt,
                    model=self.scenario.model_user,
                    timeout=90,
                    role="user",
                    max_turns=3,
                )
                self._log(f"  User simulator: {len(user_result.stdout)} chars, "
                           f"{user_result.duration_seconds}s")

                # Synthesis: agent writes canvas files from user answers
                synth_prompt = build_mycelium_prompt(
                    self.scenario, skill,
                    user_response=user_result.stdout,
                    workdir=self.workdir,
                )
                synth_result = self.runner.run(
                    synth_prompt,
                    model=self.scenario.model_mycelium,
                    timeout=timeout,
                    role="mycelium",
                    max_turns=max_turns,
                )
                self._log(f"  Synthesis: {len(synth_result.stdout)} chars, "
                           f"{synth_result.duration_seconds}s")
        else:
            # All other skills: single call with all context pre-loaded
            prompt = build_mycelium_prompt(
                self.scenario, skill,
                planted_failure=planted_failure,
                workdir=self.workdir,
            )
            self.prompt_sizes.append(len(prompt))
            result = self.runner.run(
                prompt,
                model=self.scenario.model_mycelium,
                timeout=timeout,
                role="mycelium",
                max_turns=max_turns,
            )
            self._log(f"  Mycelium agent: {len(result.stdout)} chars, "
                       f"{result.duration_seconds}s")

        # Observe workspace state after this round
        files_written = self._observe(skill)

        # Retry once if expected files were not written
        if not files_written and skill in SKILL_OUTPUTS:
            self._log(f"  RETRY: no files written for /{skill}, retrying...")
            retry_prompt = build_mycelium_prompt(
                self.scenario, skill,
                planted_failure=planted_failure,
                workdir=self.workdir,
            )
            self.runner.run(
                retry_prompt,
                model=self.scenario.model_mycelium,
                timeout=timeout,
                role="mycelium",
                max_turns=max_turns,
            )
            self._observe(skill)

    def _observe(self, skill: str) -> bool:
        """Record observations about workspace state after a round.

        Returns True if the files expected for THIS SKILL were written.
        This is skill-aware: after interview populates canvas files, a
        subsequent diamond-progress that fails to write the decision log
        will correctly return False and trigger a retry.
        """
        obs: dict = {
            "round": self.round,
            "skill": skill,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_char_count": self.prompt_sizes[-1] if self.prompt_sizes else 0,
            "checks": {},
        }

        # Determine which files this skill should have written
        expected = SKILL_OUTPUTS.get(skill, {}).get("files", [])
        skill_files_written = 0

        for rel_path in expected:
            path = self.workdir / rel_path
            written = False
            if path.exists() and path.stat().st_size > 200:
                # Decision log needs actual entries, not just boilerplate
                if "decision-log" in rel_path:
                    content = path.read_text()
                    current_entries = content.count("### ")
                    # Check if entries grew since last observation
                    prev_entries = self._prev_decision_log_entries
                    if current_entries > prev_entries:
                        written = True
                    elif prev_entries == 0:
                        # First skill to write — just check it has entries
                        written = "### " in content
                    # else: file exists but this skill didn't add new entries
                else:
                    written = True
            obs["checks"][rel_path] = written
            if written:
                skill_files_written += 1

        # Also record general workspace state for diagnostics
        canvas_dir = self.workdir / ".claude" / "canvas"
        for name in ["purpose.yml", "jobs-to-be-done.yml", "north-star.yml"]:
            path = canvas_dir / name
            obs["checks"][f"canvas/{name}"] = path.exists() and path.stat().st_size > 50

        active_file = self.workdir / ".claude" / "diamonds" / "active.yml"
        if active_file.exists():
            try:
                active = yaml.safe_load(active_file.read_text()) or {}
                diamonds = active.get("active_diamonds", [])
                obs["checks"]["diamond_count"] = len(diamonds)
                if diamonds:
                    # Track the most relevant diamond: prefer the highest-scale
                    # non-complete diamond, fall back to the last one in the list
                    active = [d for d in diamonds if d.get("phase") != "complete"]
                    d = active[-1] if active else diamonds[-1]
                    obs["checks"]["phase"] = d.get("phase", "unknown")
                    obs["checks"]["confidence"] = d.get("confidence", 0)
            except Exception:
                obs["checks"]["diamond_parse_error"] = True

        dl = self.workdir / ".claude" / "harness" / "decision-log.md"
        if dl.exists():
            entry_count = dl.read_text().count("### ")
            obs["checks"]["decision_log_entries"] = entry_count
            self._prev_decision_log_entries = entry_count

        # Track corrections for self-learning scenarios
        corrections = self.workdir / ".claude" / "memory" / "corrections.md"
        if corrections.exists():
            content = corrections.read_text()
            # Count entries using multiple formats the agent might use
            entry_count = content.count("### ")
            if entry_count == 0:
                # Fallback: count alternative correction formats
                entry_count = content.count("Mistake:") + content.count("- **")
            obs["checks"]["corrections_entries"] = entry_count

        self.observations.append(obs)

        # Return True only if the skill's expected files were written
        if not expected:
            return True  # No expectations = nothing to retry
        # Require at least half (but at least 1) of expected files
        threshold = max(1, (len(expected) + 1) // 2)
        return skill_files_written >= threshold

    def _budget_exceeded(self) -> bool:
        if self.round >= self.scenario.max_rounds:
            return True
        if self.start_time == 0:
            return False  # Session hasn't started yet
        elapsed = time.monotonic() - self.start_time
        return elapsed > self.scenario.max_time_seconds

    def _log(self, msg: str):
        if self.verbose:
            print(f"[dogfood] {msg}", file=sys.stderr)

    def cleanup(self):
        """Remove the temporary working directory."""
        if self.workdir and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)

    def _generate_proposals(self, eval_result: dict) -> list[str]:
        """Generate surface edit proposals for failed criteria."""
        proposals = []
        for criterion in eval_result["failed"]:
            if criterion == "canvas_populated":
                proposals.append("Prompt engineering: agent failed to write canvas files. Check if prompt embeds enough context or if mandatory pre-task reads consume too many turns.")
            elif criterion == "decision_log_contains":
                proposals.append("Prompt engineering: decision log missing expected content. Check if skill prompt includes clear instructions for what to log.")
            elif criterion == "confidence_decreased":
                proposals.append("Framework: agent didn't lower confidence despite negative signals. Check confidence-thresholds.yml stop conditions and mocked-persona-interview prompt.")
            elif criterion == "classification_correct":
                proposals.append("Framework: product/project type classification incorrect. Check /interview prompt for classification instructions.")
            elif criterion == "diamond_not_advanced":
                proposals.append("Framework: diamond was advanced despite insufficient evidence. Check theory-gates.md gate definitions and /diamond-progress skill.")
            elif criterion == "canvas_evidence_type":
                proposals.append("Framework: evidence type not set correctly. Check mocked-persona-interview prompt for evidence_type instructions.")
            elif criterion == "progression_blocked":
                proposals.append("Framework: progression not blocked when it should be. Check /diamond-progress gate enforcement.")
            elif criterion == "ost_has_solutions":
                proposals.append("Framework: OST missing solution candidates. Check /ost-builder prompt for solution generation instructions.")
            elif criterion == "ice_scores_present":
                proposals.append("Framework: ICE scores not computed. Check /ice-score prompt for scoring instructions.")
            elif criterion == "assumption_test_has_prediction":
                proposals.append("Framework: assumption test missing prediction. Check /assumption-test prompt for Toyota Kata prediction step.")
            elif criterion == "confidence_reflects_test":
                proposals.append("Framework: confidence not updated after assumption test. Check confidence update instructions in /assumption-test prompt.")
            elif criterion == "code_files_written":
                proposals.append("Framework: no code files written. Check /delivery-bootstrap and /reflexion prompts for code generation instructions.")
            elif criterion == "test_files_written":
                proposals.append("Framework: no test files written. Check G-V7 enforcement in /reflexion prompt.")
            elif criterion == "reflexion_iterated":
                proposals.append("Framework: reflexion loop didn't iterate. Check /reflexion prompt for iteration instructions and validation steps.")
            elif criterion == "security_issue_caught":
                proposals.append("Framework: security vulnerability not caught by reflexion. Check /reflexion prompt for OWASP validation step.")
            elif criterion == "corrections_logged":
                proposals.append("Framework: corrections.md not updated after retrospective. Check /retrospective prompt for correction logging instructions.")
            elif criterion == "dora_logged":
                proposals.append("Framework: DORA assessment not logged in decision log. Check /dora-check prompt for decision log append instructions.")
            elif criterion == "wardley_map_populated":
                proposals.append("Framework: Wardley map not written. Check /wardley-map prompt for landscape.yml generation instructions.")
            elif criterion == "team_shape_populated":
                proposals.append("Framework: team shape not assessed. Check /team-shape prompt for team-shape.yml generation.")
            elif criterion == "jtbd_mapped":
                proposals.append("Framework: JTBD not enriched. Check /jtbd-map prompt for hiring/firing/opportunity score instructions.")
            elif criterion == "launch_tier_classified":
                proposals.append("Framework: launch tier not set. Check /launch-tier prompt for go-to-market.yml generation.")
            elif criterion == "cynefin_classified":
                proposals.append("Framework: Cynefin domain not classified. Check /cynefin-classify prompt for domain assignment.")
            elif criterion == "bvssh_assessed":
                proposals.append("Framework: BVSSH not assessed. Check /bvssh-check prompt for dimension evaluation.")
            elif criterion == "privacy_assessed":
                proposals.append("Framework: privacy not assessed. Check /privacy-check prompt for PbD evaluation.")
            elif criterion == "regulatory_assessed":
                proposals.append("Framework: regulatory review not done. Check /regulatory-review prompt for compliance assessment.")
            elif criterion == "service_quality_checked":
                proposals.append("Framework: service quality not checked. Check /service-check prompt for Downe's 15 principles.")
            elif criterion == "bias_checked":
                proposals.append("Framework: bias check not run. Check /bias-check prompt for cognitive bias audit.")
            elif criterion == "dod_checked":
                proposals.append("Framework: DoD not validated. Check /definition-of-done prompt for checklist instructions.")
            elif criterion == "market_regression_logged":
                proposals.append("Framework: market regression not considered. Check /launch-tier prompt for regression trigger handling.")
            else:
                proposals.append(f"Unknown criterion '{criterion}' failed. Manual investigation needed.")
        return proposals

    @staticmethod
    def _empty_template(filename: str) -> str:
        if filename == "active.yml":
            return "# Diamond state\nactive_diamonds: []\n"
        if filename == "decision-log.md":
            return "# Decision Log\n\nDecisions are logged below.\n"
        return ""

    @staticmethod
    def _empty_canvas(stem: str) -> str:
        return f"# {stem.replace('-', ' ').title()}\n# Auto-generated empty template\n"


def generate_report(results: list[dict], output_path: Path | None = None) -> str:
    """Generate a summary report from multiple scenario results."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_score = sum(r["score"] for r in results) / total if total else 0

    lines = [
        f"# Auto-Dogfood Report",
        f"",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"**Scenarios**: {total}",
        f"**Passed**: {passed}/{total} ({passed/total:.0%})" if total else "",
        f"**Average score**: {avg_score:.0%}",
        f"",
        f"## Results",
        f"",
        f"| Scenario | Score | Passed | Failed | Time |",
        f"|----------|-------|--------|--------|------|",
    ]

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        n_passed = len(r["criteria"]["passed"])
        n_failed = len(r["criteria"]["failed"])
        lines.append(
            f"| {r['scenario'][:40]} | {r['score']:.0%} ({status}) | "
            f"{n_passed} | {n_failed} | {r['time_seconds']:.0f}s |"
        )

    # Failed criteria summary
    all_failures: dict[str, int] = {}
    for r in results:
        for f in r["criteria"]["failed"]:
            all_failures[f] = all_failures.get(f, 0) + 1

    if all_failures:
        lines.extend([
            "", "## Common Failures", "",
            "| Criterion | Frequency |",
            "|-----------|-----------|",
        ])
        for criterion, count in sorted(all_failures.items(), key=lambda x: -x[1]):
            lines.append(f"| {criterion} | {count}/{total} |")

    report = "\n".join(lines) + "\n"

    if output_path:
        output_path.write_text(report)

    return report


def compare_runs(baseline_path: Path, variant_path: Path) -> str:
    """Compare two run results for A/B analysis."""
    with open(baseline_path) as f:
        baseline = json.load(f)
    with open(variant_path) as f:
        variant = json.load(f)

    b_scores = {r["scenario"]: r["score"] for r in baseline}
    v_scores = {r["scenario"]: r["score"] for r in variant}

    lines = [
        "# Auto-Dogfood Comparison",
        "",
        "| Scenario | Baseline | Variant | Delta |",
        "|----------|----------|---------|-------|",
    ]

    all_scenarios = sorted(set(b_scores) | set(v_scores))
    for s in all_scenarios:
        b = b_scores.get(s)
        v = v_scores.get(s)
        b_str = f"{b:.0%}" if b is not None else "—"
        v_str = f"{v:.0%}" if v is not None else "—"
        if b is not None and v is not None:
            delta = v - b
            sign = "+" if delta >= 0 else ""
            delta_str = f"{sign}{delta:.0%}"
        else:
            delta_str = "—"
        lines.append(f"| {s[:40]} | {b_str} | {v_str} | {delta_str} |")

    b_avg = sum(b_scores.values()) / len(b_scores) if b_scores else 0
    v_avg = sum(v_scores.values()) / len(v_scores) if v_scores else 0
    lines.append(f"| **Average** | **{b_avg:.0%}** | **{v_avg:.0%}** | **{v_avg - b_avg:+.0%}** |")

    return "\n".join(lines) + "\n"


def run_scenario(scenario_path: str, verbose: bool = False, keep_workdir: bool = False) -> dict:
    """Run a single scenario and return the result dict.

    Top-level function so ProcessPoolExecutor can pickle it.
    """
    scenario = Scenario.load(scenario_path)
    session = DogfoodSession(scenario, verbose=verbose)
    try:
        return session.run()
    except Exception as exc:
        return {
            "scenario": Path(scenario_path).stem,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "score": 0.0,
            "criteria": {"passed": [], "failed": ["execution_error"]},
            "rounds_used": 0,
            "time_seconds": 0,
            "error": str(exc),
        }
    finally:
        if not keep_workdir:
            session.cleanup()


def cmd_run(args):
    scenario = Scenario.load(args.scenario)
    session = DogfoodSession(scenario, verbose=args.verbose)

    try:
        result = session.run()
    finally:
        if not args.keep_workdir:
            session.cleanup()

    # Write result
    results_dir = Path(args.output)
    results_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(args.scenario).stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    result_path = results_dir / f"{ts}-{stem}.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n")

    print(f"Score: {result['score']:.0%} ({'PASS' if result['passed'] else 'FAIL'})")
    print(f"Result: {result_path}")

    if result["criteria"]["failed"]:
        print(f"Failed: {', '.join(result['criteria']['failed'])}")

    return 0 if result["passed"] else 1


def cmd_run_all(args):
    scenario_dir = Path(args.scenario_dir)
    scenario_files = sorted(scenario_dir.glob("*.yml"))

    if not scenario_files:
        print(f"No scenarios found in {scenario_dir}")
        return 1

    results = []
    for path in scenario_files:
        print(f"\n{'='*60}")
        print(f"Running: {path.name}")
        print(f"{'='*60}")

        scenario = Scenario.load(path)
        session = DogfoodSession(scenario, verbose=args.verbose)

        try:
            result = session.run()
            results.append(result)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            results.append({
                "scenario": path.stem,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "passed": False,
                "score": 0.0,
                "criteria": {"passed": [], "failed": ["execution_error"]},
                "rounds_used": 0,
                "time_seconds": 0,
                "error": str(exc),
            })
        finally:
            if not args.keep_workdir:
                session.cleanup()

    # Write aggregate results
    results_dir = Path(args.output)
    results_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    aggregate_path = results_dir / f"{ts}-aggregate.json"
    aggregate_path.write_text(json.dumps(results, indent=2) + "\n")

    report = generate_report(results, results_dir / f"{ts}-report.md")
    print(report)

    return 0 if all(r["passed"] for r in results) else 1


def cmd_run_parallel(args):
    """Run all scenarios concurrently using a process pool."""
    scenario_dir = Path(args.scenario_dir)
    scenario_files = sorted(scenario_dir.glob("*.yml"))

    if not scenario_files:
        print(f"No scenarios found in {scenario_dir}")
        return 1

    workers = min(args.workers, len(scenario_files))
    print(f"Running {len(scenario_files)} scenarios with {workers} parallel workers\n")

    results = []
    start = time.monotonic()

    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_to_name = {
            pool.submit(
                run_scenario,
                str(path),
                args.verbose,
                args.keep_workdir,
            ): path.name
            for path in scenario_files
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"  CRASH  {name}: {exc}", file=sys.stderr)
                result = {
                    "scenario": Path(name).stem,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "passed": False,
                    "score": 0.0,
                    "criteria": {"passed": [], "failed": ["worker_crash"]},
                    "rounds_used": 0,
                    "time_seconds": 0,
                    "error": str(exc),
                }
            status = "PASS" if result["passed"] else "FAIL"
            print(f"  {status}  {name}  ({result['score']:.0%}, {result.get('time_seconds', 0):.0f}s)")
            results.append(result)

    wall_time = round(time.monotonic() - start, 1)
    print(f"\nAll scenarios complete in {wall_time}s wall-clock time")

    # Write aggregate results
    results_dir = Path(args.output)
    results_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    aggregate_path = results_dir / f"{ts}-parallel-aggregate.json"
    aggregate_path.write_text(json.dumps(results, indent=2) + "\n")

    report = generate_report(results, results_dir / f"{ts}-parallel-report.md")
    print(report)

    return 0 if all(r["passed"] for r in results) else 1


def cmd_report(args):
    results_dir = Path(args.results_dir)
    all_results = []

    for path in sorted(results_dir.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            all_results.extend(data)
        elif isinstance(data, dict) and "scenario" in data:
            all_results.append(data)

    if not all_results:
        print(f"No results found in {results_dir}")
        return 1

    report = generate_report(all_results)
    print(report)
    return 0


def cmd_compare(args):
    report = compare_runs(Path(args.baseline), Path(args.variant))
    print(report)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Mycelium Auto-Dogfood Orchestrator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared args added to each subparser (argparse doesn't propagate
    # parent-level flags reliably to subcommands)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-v", "--verbose", action="store_true")
    shared.add_argument("--keep-workdir", action="store_true",
                        help="Don't delete the temporary workdir after run")

    # run
    p_run = subparsers.add_parser("run", parents=[shared], help="Run a single scenario")
    p_run.add_argument("scenario", help="Path to scenario YAML")
    p_run.add_argument("-o", "--output", default=".claude/auto-dogfood/results",
                       help="Output directory for results")

    # run-all
    p_all = subparsers.add_parser("run-all", parents=[shared], help="Run all scenarios in a directory")
    p_all.add_argument("scenario_dir", help="Directory containing scenario YAMLs")
    p_all.add_argument("-o", "--output", default=".claude/auto-dogfood/results",
                       help="Output directory for results")

    # run-parallel
    p_par = subparsers.add_parser("run-parallel", parents=[shared],
                                  help="Run all scenarios in parallel")
    p_par.add_argument("scenario_dir", help="Directory containing scenario YAMLs")
    p_par.add_argument("-w", "--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    p_par.add_argument("-o", "--output", default=".claude/auto-dogfood/results",
                       help="Output directory for results")

    # report
    p_rep = subparsers.add_parser("report", parents=[shared], help="Generate report from results")
    p_rep.add_argument("results_dir", help="Directory containing result JSONs")

    # compare
    p_cmp = subparsers.add_parser("compare", parents=[shared], help="Compare two run results")
    p_cmp.add_argument("baseline", help="Baseline results JSON")
    p_cmp.add_argument("variant", help="Variant results JSON")

    args = parser.parse_args()

    handlers = {
        "run": cmd_run,
        "run-all": cmd_run_all,
        "run-parallel": cmd_run_parallel,
        "report": cmd_report,
        "compare": cmd_compare,
    }

    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
