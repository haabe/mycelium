"""Claude Code session runner — wraps `claude -p` for non-interactive execution."""

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool = False


@dataclass
class TokenTracker:
    mycelium_agent: int = 0
    user_simulator: int = 0

    @property
    def total(self) -> int:
        return self.mycelium_agent + self.user_simulator

    def to_dict(self) -> dict:
        return {
            "mycelium_agent": self.mycelium_agent,
            "user_simulator": self.user_simulator,
            "total": self.total,
        }


class ClaudeRunner:
    """Runs Claude Code sessions via `claude -p` (print/pipe mode)."""

    def __init__(self, workdir: Path, allowed_tools: list[str] | None = None):
        self.workdir = workdir
        self.allowed_tools = allowed_tools or [
            "Read", "Write", "Edit", "Glob", "Grep", "Bash",
        ]
        self.token_tracker = TokenTracker()

    def run(
        self,
        prompt: str,
        model: str = "sonnet",
        timeout: int = 120,
        role: str = "mycelium",
    ) -> RunResult:
        """Run a single Claude Code session and return the result.

        Args:
            prompt: The prompt to send.
            model: Model to use (sonnet, haiku, opus).
            timeout: Max seconds before killing the process.
            role: 'mycelium' or 'user' — for token tracking.
        """
        cmd = [
            "claude", "-p", prompt,
            "--model", model,
            "--output-format", "text",
            "--allowedTools", ",".join(self.allowed_tools),
        ]

        start = time.monotonic()
        timed_out = False

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            stdout = exc.stdout.decode() if exc.stdout else ""
            stderr = exc.stderr.decode() if exc.stderr else ""

        duration = time.monotonic() - start

        return RunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=round(duration, 2),
            timed_out=timed_out,
        )
