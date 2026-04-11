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
from datetime import datetime, timezone
from pathlib import Path

import yaml

from lib.evaluator import Evaluator
from lib.prompts import build_mycelium_prompt, build_user_prompt
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
        self.round = 0
        self.start_time: float = 0

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

        # Reset canvas to empty templates
        canvas_dir = workdir / ".claude" / "canvas"
        if canvas_dir.is_dir():
            for yml in canvas_dir.glob("*.yml"):
                yml.write_text(self._empty_canvas(yml.stem))

        # Init git so hooks and tools work correctly
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

        for step in self.scenario.journey:
            if self._budget_exceeded():
                self._log("Budget exceeded, stopping.")
                break

            self._log(f"Step: /{step.skill} (rounds={step.rounds})")
            planted = None
            if step.planted_failure:
                planted = self.scenario.get_failure_for_skill(step.skill)

            for r in range(step.rounds):
                self.round += 1
                self._run_round(step.skill, planted_failure=planted)

        # Evaluate
        evaluator = Evaluator(self.workdir)
        eval_result = evaluator.evaluate(self.scenario.success_criteria)

        elapsed = round(time.monotonic() - self.start_time, 1)
        self._log(
            f"Done. Score: {eval_result['score']:.0%} "
            f"({len(eval_result['passed'])}/{len(eval_result['passed']) + len(eval_result['failed'])})"
        )

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
            "workdir": str(self.workdir),
        }

    def _run_round(
        self,
        skill: str,
        planted_failure=None,
    ):
        """Execute one orchestrator round (mycelium agent + optional user sim)."""
        # Step 1: Mycelium agent executes the skill
        mycelium_prompt = build_mycelium_prompt(
            self.scenario, skill, planted_failure=planted_failure,
        )
        mycelium_result = self.runner.run(
            mycelium_prompt,
            model=self.scenario.model_mycelium,
            timeout=180,
            role="mycelium",
        )

        self._log(f"  Mycelium agent: {len(mycelium_result.stdout)} chars, "
                   f"{mycelium_result.duration_seconds}s")

        # Step 2: If the skill involves user interaction, simulate user
        if skill in ("interview", "mocked-persona-interview") and mycelium_result.stdout:
            user_prompt = build_user_prompt(
                self.scenario, skill, mycelium_result.stdout,
            )
            user_result = self.runner.run(
                user_prompt,
                model=self.scenario.model_user,
                timeout=60,
                role="user",
            )

            self._log(f"  User simulator: {len(user_result.stdout)} chars, "
                       f"{user_result.duration_seconds}s")

            # Step 3: Feed user response back to Mycelium agent
            followup_prompt = build_mycelium_prompt(
                self.scenario, skill,
                user_response=user_result.stdout,
                planted_failure=planted_failure,
            )
            followup_result = self.runner.run(
                followup_prompt,
                model=self.scenario.model_mycelium,
                timeout=180,
                role="mycelium",
            )

            self._log(f"  Mycelium followup: {len(followup_result.stdout)} chars, "
                       f"{followup_result.duration_seconds}s")

        # Observe workspace state after this round
        self._observe(skill)

    def _observe(self, skill: str):
        """Record observations about workspace state after a round."""
        obs: dict = {
            "round": self.round,
            "skill": skill,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        # Check canvas files
        canvas_dir = self.workdir / ".claude" / "canvas"
        for name in ["purpose.yml", "jobs-to-be-done.yml", "north-star.yml",
                      "landscape.yml", "user-needs.yml"]:
            path = canvas_dir / name
            obs["checks"][f"canvas_{name}"] = (
                path.exists() and path.stat().st_size > 200
            )

        # Check diamond state
        active_file = self.workdir / ".claude" / "diamonds" / "active.yml"
        if active_file.exists():
            try:
                active = yaml.safe_load(active_file.read_text()) or {}
                diamonds = active.get("active_diamonds", [])
                obs["checks"]["diamond_count"] = len(diamonds)
                if diamonds:
                    d = diamonds[0]
                    obs["checks"]["phase"] = d.get("phase", "unknown")
                    obs["checks"]["confidence"] = d.get("confidence", 0)
                    obs["checks"]["scale"] = d.get("scale", "unknown")
            except Exception:
                obs["checks"]["diamond_parse_error"] = True

        # Check decision log
        dl = self.workdir / ".claude" / "harness" / "decision-log.md"
        if dl.exists():
            content = dl.read_text()
            obs["checks"]["decision_log_entries"] = content.count("### ")

        self.observations.append(obs)

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
    parser.add_argument("-v", "--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser("run", help="Run a single scenario")
    p_run.add_argument("scenario", help="Path to scenario YAML")
    p_run.add_argument("-o", "--output", default=".claude/auto-dogfood/results",
                       help="Output directory for results")
    p_run.add_argument("--keep-workdir", action="store_true",
                       help="Don't delete the temporary workdir after run")

    # run-all
    p_all = subparsers.add_parser("run-all", help="Run all scenarios in a directory")
    p_all.add_argument("scenario_dir", help="Directory containing scenario YAMLs")
    p_all.add_argument("-o", "--output", default=".claude/auto-dogfood/results",
                       help="Output directory for results")
    p_all.add_argument("--keep-workdir", action="store_true")

    # report
    p_rep = subparsers.add_parser("report", help="Generate report from results")
    p_rep.add_argument("results_dir", help="Directory containing result JSONs")

    # compare
    p_cmp = subparsers.add_parser("compare", help="Compare two run results")
    p_cmp.add_argument("baseline", help="Baseline results JSON")
    p_cmp.add_argument("variant", help="Variant results JSON")

    args = parser.parse_args()

    handlers = {
        "run": cmd_run,
        "run-all": cmd_run_all,
        "report": cmd_report,
        "compare": cmd_compare,
    }

    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()
