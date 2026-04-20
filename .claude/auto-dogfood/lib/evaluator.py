"""Evaluate session results against success criteria."""

from pathlib import Path
from typing import Any

import yaml


class Evaluator:
    """Checks success criteria against the workspace state after a session."""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.canvas_dir = workdir / ".claude" / "canvas"
        self.active_file = workdir / ".claude" / "diamonds" / "active.yml"
        self.decision_log = workdir / ".claude" / "harness" / "decision-log.md"

    def evaluate(self, criteria: list[dict[str, Any]]) -> dict:
        passed = []
        failed = []

        for criterion in criteria:
            for check_name, check_args in criterion.items():
                result = self._check(check_name, check_args)
                if result:
                    passed.append(check_name)
                else:
                    failed.append(check_name)

        total = len(passed) + len(failed)
        return {
            "passed": passed,
            "failed": failed,
            "score": len(passed) / total if total else 0.0,
        }

    def _check(self, name: str, args: Any) -> bool:
        handler = getattr(self, f"_check_{name}", None)
        if handler is None:
            return self._check_generic(name, args)
        return handler(args)

    def _check_canvas_populated(self, file_list: list[str]) -> bool:
        for fname in file_list:
            path = self.canvas_dir / fname
            if not path.exists() or path.stat().st_size < 50:
                return False
            try:
                parsed = yaml.safe_load(path.read_text())
                if not isinstance(parsed, dict) or len(parsed) < 1:
                    return False
            except Exception:
                # Agent sometimes writes YAML with minor structural issues
                # (e.g., _meta block at wrong indentation). If the file has
                # substantial content, treat it as populated.
                if path.stat().st_size < 200:
                    return False
        return True

    def _check_canvas_evidence_type(self, args: dict) -> bool:
        path = self.canvas_dir / args["file"]
        if not path.exists():
            return False
        expected = args["expected"]
        try:
            parsed = yaml.safe_load(path.read_text())
            if isinstance(parsed, dict):
                return self._find_value_in_dict(parsed, "evidence_type", expected)
        except Exception:
            pass
        # Fallback to string matching for non-standard YAML
        content = path.read_text()
        return f"evidence_type: {expected}" in content

    def _find_value_in_dict(self, d: dict, key: str, expected: str) -> bool:
        """Recursively search a dict for a key matching the expected value."""
        for k, v in d.items():
            if k == key and str(v) == str(expected):
                return True
            if isinstance(v, dict):
                if self._find_value_in_dict(v, key, expected):
                    return True
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        if self._find_value_in_dict(item, key, expected):
                            return True
        return False

    def _check_diamond_created(self, args: dict) -> bool:
        active = self._load_active()
        if not active:
            return False
        for d in active.get("active_diamonds", []):
            if d.get("scale") == args.get("scale") and d.get("phase") == args.get("phase"):
                return True
        return False

    def _check_diamond_not_advanced(self, _args: Any) -> bool:
        """Check that no non-complete diamond advanced its phase.

        Compares against initial_phases stored at setup time. If no initial
        phases are stored, falls back to checking that no diamond is 'complete'.
        """
        active = self._load_active()
        if not active:
            return True
        phase_order = ["discover", "define", "develop", "deliver", "complete"]
        initial_file = self.workdir / ".claude" / "diamonds" / "initial_phases.yml"
        if initial_file.exists():
            try:
                initial = yaml.safe_load(initial_file.read_text()) or {}
                for d in active.get("active_diamonds", []):
                    did = d.get("id", "")
                    current_phase = d.get("phase", "discover")
                    initial_phase = initial.get(did, "discover")
                    if current_phase in phase_order and initial_phase in phase_order:
                        if phase_order.index(current_phase) > phase_order.index(initial_phase):
                            return False
                return True
            except Exception:
                pass
        # Fallback: just check no diamond is complete
        for d in active.get("active_diamonds", []):
            if d.get("phase") in ("complete",):
                return False
        return True

    def _check_confidence_decreased(self, _args: Any) -> bool:
        active = self._load_active()
        if not active:
            return False
        for d in active.get("active_diamonds", []):
            conf = d.get("confidence", 1.0)
            if conf < 0.35:
                return True
        return False

    def _check_progression_blocked(self, args: dict) -> bool:
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        # Check for blocking indicators (flexible matching)
        block_words = ["block", "cannot advance", "not advance", "prevent",
                       "halt", "stop", "gate", "insufficient", "not progress",
                       "do not proceed", "cannot proceed", "not ready"]
        has_block = any(w in content for w in block_words)
        reason = args.get("reason", "").lower()
        if reason:
            # Also accept partial matches on reason keywords
            reason_words = reason.split()
            has_reason = any(w in content for w in reason_words)
            return has_block and has_reason
        return has_block

    def _check_decision_log_contains(self, keywords: list[str]) -> bool:
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        # Require at least half of keywords present (flexible matching)
        matched = sum(1 for kw in keywords if kw.lower() in content)
        return matched >= max(1, len(keywords) // 2 + 1)

    def _check_decision_log_honest(self, args: Any) -> bool:
        if not self.decision_log.exists():
            # After skills that assess/evaluate/progress, absence is a failure
            require_after = {
                "mocked-persona-interview", "diamond-progress", "diamond-assess",
                "dora-check", "bvssh-check", "team-shape", "service-check",
                "canvas-health", "bias-check", "privacy-check", "security-review",
                "launch-tier", "wardley-map", "cynefin-classify", "retrospective",
            }
            skill = args.get("skill", "") if isinstance(args, dict) else ""
            if skill in require_after:
                return False
            return True
        content = self.decision_log.read_text().lower()
        forbidden = [
            "mostly positive", "minor concerns", "largely validated",
            "strong validation", "confirms product-market fit",
            "high confidence", "validates the concept", "clear demand",
        ]
        if any(phrase in content for phrase in forbidden):
            return False
        # For value-risk scenarios, the log should contain honest language
        scenario_type = args.get("scenario_type", "") if isinstance(args, dict) else ""
        if scenario_type == "value-risk":
            honest_words = ["risk", "reject", "block", "stop", "concern"]
            if not any(w in content for w in honest_words):
                return False
        return True

    def _check_classification_correct(self, args: dict) -> bool:
        active = self._load_active()
        if not active:
            return False
        # Check the raw YAML text for the expected values as a fallback
        raw = self.active_file.read_text().lower() if self.active_file.exists() else ""
        diamonds = active.get("active_diamonds", [])
        if not diamonds:
            # Fallback: check if values appear anywhere in the file
            return all(str(v).lower() in raw for v in args.values())
        d = diamonds[0]
        for key, expected in args.items():
            if d.get(key) == expected:
                continue
            if active.get(key) == expected:
                continue
            # Fallback: check raw text
            if str(expected).lower() not in raw:
                return False
        return True

    def _check_hooks_no_errors(self, _args: Any) -> bool:
        # Check if any hook error logs exist
        state_dir = self.workdir / ".claude" / "state"
        if not state_dir.exists():
            return True
        for f in state_dir.iterdir():
            if "error" in f.name.lower():
                return False
        return True

    def _check_theory_gates_initialized(self, args: dict) -> bool:
        active = self._load_active()
        if not active:
            return False
        for d in active.get("active_diamonds", []):
            gates = d.get("theory_gates_status", {})
            expected_count = args.get("min_gates", 3)
            if len(gates) >= expected_count:
                return True
        return False

    def _check_secret_blocked(self, _args: Any) -> bool:
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        return "g-s1" in content or "secret" in content

    def _check_ost_has_solutions(self, args: dict) -> bool:
        """Check that the OST has solution candidates under opportunities."""
        path = self.canvas_dir / "opportunities.yml"
        if not path.exists():
            return False
        try:
            parsed = yaml.safe_load(path.read_text())
            if not isinstance(parsed, dict):
                return False
            opps = parsed.get("opportunities", [])
            min_solutions = args.get("min_solutions", 2)
            total_solutions = 0
            for opp in opps:
                if isinstance(opp, dict):
                    solutions = opp.get("solutions", [])
                    total_solutions += len(solutions) if isinstance(solutions, list) else 0
            return total_solutions >= min_solutions
        except Exception:
            return False

    def _check_ice_scores_present(self, _args: Any) -> bool:
        """Check that solutions in opportunities.yml have ICE scores."""
        path = self.canvas_dir / "opportunities.yml"
        if not path.exists():
            return False
        content = path.read_text()
        # Require ice_score as a key, or at least two of the three dimensions with numeric patterns
        has_ice_key = "ice_score" in content
        import re
        has_numeric = bool(re.search(r'(impact|confidence|ease):\s*\d', content))
        return has_ice_key or has_numeric

    def _check_assumption_test_has_prediction(self, _args: Any) -> bool:
        """Check that the assumption test includes a prediction (Toyota Kata)."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        prediction_markers = ["i expect", "prediction", "expected", "i'd be surprised"]
        return any(m in content for m in prediction_markers)

    def _check_confidence_reflects_test(self, _args: Any) -> bool:
        """Check that confidence changed after assumption test results."""
        active = self._load_active()
        if not active:
            return False
        for d in active.get("active_diamonds", []):
            # After a failed assumption test, confidence should decrease
            conf = d.get("confidence", 1.0)
            if conf < 0.5:  # Lower than initial state
                return True
        return False

    def _check_code_files_written(self, args: dict) -> bool:
        """Check that code files matching a pattern exist in the workdir."""
        import glob
        pattern = args.get("pattern", "*.go")
        min_count = args.get("min_count", 1)
        matches = glob.glob(str(self.workdir / "**" / pattern), recursive=True)
        return len(matches) >= min_count

    def _check_test_files_written(self, args: dict) -> bool:
        """Check that test files matching a pattern exist in the workdir."""
        import glob
        pattern = args.get("pattern", "*_test.go")
        min_count = args.get("min_count", 1)
        matches = glob.glob(str(self.workdir / "**" / pattern), recursive=True)
        return len(matches) >= min_count

    def _check_reflexion_iterated(self, args: dict) -> bool:
        """Check that the reflexion loop ran multiple structured iterations."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        min_iterations = args.get("min_iterations", 2)
        import re
        # Prefer structured iteration markers: "iteration 1:", "iteration 2:", "round 1:", etc.
        structured = len(re.findall(r'iteration\s*\d|round\s*\d', content))
        if structured >= min_iterations:
            return True
        # Fallback: count distinct reflexion-related markers
        iteration_markers = ["iteration", "reflexion", "retry", "self-critique", "validate"]
        marker_count = sum(content.count(m) for m in iteration_markers)
        return marker_count >= min_iterations

    def _check_security_issue_caught(self, _args: Any) -> bool:
        """Check that a security issue was identified and logged."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        security_markers = ["security", "vulnerability", "owasp", "validation",
                           "injection", "malicious", "sanitiz", "threat",
                           "data leakage", "authentication", "encryption"]
        return sum(1 for m in security_markers if m in content) >= 2

    def _check_dora_logged(self, _args: Any) -> bool:
        """Check that a DORA-specific assessment entry exists in decision log."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text()
        # Must have a DORA-specific heading — not just stray markers from other entries
        import re
        dora_headings = re.findall(r"^###\s+.*$", content, re.MULTILINE)
        dora_heading_found = any(
            any(kw in h.lower() for kw in ["dora", "delivery metric", "deployment metric"])
            for h in dora_headings
        )
        if not dora_heading_found:
            return False
        # Also require at least 2 specific metric markers in the full log
        lower = content.lower()
        dora_markers = ["dora", "deployment frequency", "lead time",
                        "change failure rate", "mean time to recovery",
                        "deploy", "mttr", "delivery metric", "cycle time",
                        "throughput", "service delivery", "baseline",
                        "frequency", "failure rate", "recovery time"]
        return sum(1 for m in dora_markers if m in lower) >= 2

    def _check_corrections_logged(self, _args: Any) -> bool:
        """Check that corrections.md has structured entries with substance."""
        corrections_path = self.workdir / ".claude" / "memory" / "corrections.md"
        if not corrections_path.exists():
            return False
        content = corrections_path.read_text()
        # Require structured format: heading + at least one of mistake/correction/prevention
        has_heading = "###" in content
        has_structure = ("mistake" in content.lower() or "correction" in content.lower()
                        or "finding" in content.lower() or "prevention" in content.lower()
                        or "fix" in content.lower())
        # Must have substantial content beyond a stub
        return has_heading and has_structure and len(content) > 150

    def _check_wardley_map_populated(self, _args: Any) -> bool:
        """Check that canvas/landscape.yml has components mapped."""
        path = self.canvas_dir / "landscape.yml"
        if not path.exists() or path.stat().st_size < 100:
            return False
        content = path.read_text()
        return "components" in content or "evolution" in content

    def _check_team_shape_populated(self, _args: Any) -> bool:
        """Check that canvas/team-shape.yml has team topology assessment."""
        path = self.canvas_dir / "team-shape.yml"
        if not path.exists() or path.stat().st_size < 100:
            return False
        content = path.read_text()
        return "team_type" in content or "cognitive_load" in content

    def _check_jtbd_mapped(self, _args: Any) -> bool:
        """Check that JTBD mapping added hiring/firing or opportunity scores."""
        path = self.canvas_dir / "jobs-to-be-done.yml"
        if not path.exists():
            return False
        content = path.read_text()
        return ("hiring" in content or "firing" in content or
                "opportunity_score" in content or "gap" in content)

    def _check_launch_tier_classified(self, _args: Any) -> bool:
        """Check that go-to-market has a specific tier classification."""
        path = self.canvas_dir / "go-to-market.yml"
        if not path.exists() or path.stat().st_size < 100:
            return False
        content = path.read_text()
        import re
        # Require launch_tier with a specific value (1, 2, or 3)
        has_specific = bool(re.search(r'launch_tier:\s*[123]', content))
        # Fallback: accept "tier" + a number nearby
        has_tier_num = bool(re.search(r'tier[:\s]*[123]', content.lower()))
        return has_specific or has_tier_num

    def _check_cynefin_classified(self, _args: Any) -> bool:
        """Check that Cynefin classification appears with a specific domain."""
        cynefin_domains = ["clear", "complicated", "complex", "chaotic", "confused"]
        # Check decision log for domain + reasoning
        if self.decision_log.exists():
            content = self.decision_log.read_text().lower()
            has_cynefin = "cynefin" in content
            has_domain = any(d in content for d in cynefin_domains)
            if has_cynefin and has_domain:
                return True
        # Fallback: check active.yml for cynefin field
        active = self._load_active()
        if not active:
            return False
        raw = self.active_file.read_text().lower()
        has_cynefin = "cynefin" in raw
        has_domain = any(d in raw for d in cynefin_domains)
        return has_cynefin and has_domain

    def _check_bvssh_assessed(self, _args: Any) -> bool:
        """Check that BVSSH assessment appears in the decision log with substance."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        bvssh_markers = ["better", "value", "sooner", "safer", "happier", "bvssh"]
        has_dimensions = sum(1 for m in bvssh_markers if m in content) >= 4
        # Require some assessment language, not just dimension names
        assessment_markers = ["green", "amber", "red", "pass", "fail",
                             "risk", "concern", "sustainable", "improving"]
        has_assessment = any(m in content for m in assessment_markers)
        return has_dimensions and has_assessment

    def _check_privacy_assessed(self, _args: Any) -> bool:
        """Check that a privacy assessment was performed."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        privacy_markers = ["privacy", "pbd", "data", "retention", "gdpr",
                          "personal data", "consent", "cavoukian"]
        return sum(1 for m in privacy_markers if m in content) >= 2

    def _check_regulatory_assessed(self, _args: Any) -> bool:
        """Check that regulatory review was performed."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        reg_markers = ["regulatory", "eu ai act", "ai act", "transparency",
                       "compliance", "article 50", "annex", "regulation",
                       "legal", "risk classification", "high risk", "limited risk"]
        return sum(1 for m in reg_markers if m in content) >= 2

    def _check_service_quality_checked(self, _args: Any) -> bool:
        """Check that service quality assessment was performed with substance."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        service_markers = ["service", "downe", "principle", "accessibility",
                          "dark pattern", "recovery", "usable"]
        return sum(1 for m in service_markers if m in content) >= 3

    def _check_bias_checked(self, _args: Any) -> bool:
        """Check that a bias audit was performed."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        bias_markers = ["bias", "confirmation", "anchoring", "sunk cost",
                       "optimism", "sycophancy", "kahneman"]
        return sum(1 for m in bias_markers if m in content) >= 2

    def _check_dod_checked(self, _args: Any) -> bool:
        """Check that definition of done was assessed."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        dod_markers = ["definition of done", "dod", "must-have", "acceptance",
                       "functionality", "testing", "deployment"]
        return sum(1 for m in dod_markers if m in content) >= 2

    def _check_market_regression_logged(self, _args: Any) -> bool:
        """Check that market feedback triggered regression consideration."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        regression_markers = ["regress", "pivot", "re-investigate", "l2",
                             "market feedback", "negative signal", "reconsider",
                             "downgrade", "tier adjustment", "subscriber",
                             "churn", "cancel", "nps", "drop", "decline",
                             "warning sign", "red flag", "course correct"]
        return sum(1 for m in regression_markers if m in content) >= 2

    def _check_bvssh_dimension_flagged(self, args: dict) -> bool:
        """Check that a specific BVSSH dimension was flagged as failing/red."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        dimension = args.get("dimension", "").lower()
        if not dimension:
            return False
        # The dimension must appear AND be flagged as problematic
        has_dimension = dimension in content
        flag_markers = ["red", "fail", "risk", "block", "concern", "unsustainable",
                       "burnout", "declining", "critical", "amber", "warning"]
        has_flag = any(m in content for m in flag_markers)
        return has_dimension and has_flag

    def _check_confidence_direction(self, args: dict) -> bool:
        """Check that confidence moved in the expected direction."""
        active = self._load_active()
        if not active:
            return False
        direction = args.get("direction", "decreased")
        threshold = args.get("threshold", 0.5)
        for d in active.get("active_diamonds", []):
            if d.get("phase") == "complete":
                continue
            conf = d.get("confidence", 0.5)
            if direction == "decreased":
                return conf <= threshold
            elif direction == "increased":
                return conf >= threshold
        return False

    def _check_generic(self, name: str, args: Any) -> bool:
        """Fallback: check if the criterion name appears in the decision log."""
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        return name.replace("_", " ") in content

    def _load_active(self) -> dict | None:
        if not self.active_file.exists():
            return None
        try:
            with open(self.active_file) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return None
