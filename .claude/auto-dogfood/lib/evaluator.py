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
            if not path.exists() or path.stat().st_size < 200:
                return False
        return True

    def _check_canvas_evidence_type(self, args: dict) -> bool:
        path = self.canvas_dir / args["file"]
        if not path.exists():
            return False
        content = path.read_text()
        expected = args["expected"]
        return f"evidence_type: {expected}" in content

    def _check_diamond_created(self, args: dict) -> bool:
        active = self._load_active()
        if not active:
            return False
        for d in active.get("active_diamonds", []):
            if d.get("scale") == args.get("scale") and d.get("phase") == args.get("phase"):
                return True
        return False

    def _check_diamond_not_advanced(self, _args: Any) -> bool:
        active = self._load_active()
        if not active:
            return True
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
        reason = args.get("reason", "").lower()
        return "block" in content and (not reason or reason in content)

    def _check_decision_log_contains(self, keywords: list[str]) -> bool:
        if not self.decision_log.exists():
            return False
        content = self.decision_log.read_text().lower()
        return all(kw.lower() in content for kw in keywords)

    def _check_decision_log_honest(self, _args: Any) -> bool:
        if not self.decision_log.exists():
            return True
        content = self.decision_log.read_text().lower()
        forbidden = ["mostly positive", "minor concerns", "largely validated"]
        return not any(phrase in content for phrase in forbidden)

    def _check_classification_correct(self, args: dict) -> bool:
        active = self._load_active()
        if not active:
            return False
        diamonds = active.get("active_diamonds", [])
        if not diamonds:
            return False
        d = diamonds[0]
        for key, expected in args.items():
            if d.get(key) != expected:
                root_val = active.get(key)
                if root_val != expected:
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
