"""Claude Code session runner — wraps `claude -p` for non-interactive execution."""

import json
import subprocess
import time
from dataclasses import dataclass
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
    """Runs Claude Code sessions via `claude -p` (print/pipe mode).

    Key design decisions (learned from testing):
    - Match the framework's own permission mode (acceptEdits from settings.json)
    - Do NOT use --allowedTools (it's a permission rule, not a tool filter —
      in -p mode, unlisted tools cause the agent to hang waiting for
      human approval that never comes)
    - Use --max-turns to prevent runaway sessions
    - Keep all framework hooks and CLAUDE.md intact — the dogfood tests the
      real framework, not a stripped-down version
    """

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.token_tracker = TokenTracker()

    def run(
        self,
        prompt: str,
        model: str = "sonnet",
        timeout: int = 120,
        role: str = "mycelium",
        max_turns: int = 0,
    ) -> RunResult:
        """Run a single Claude Code session and return the result.

        Args:
            prompt: The prompt to send.
            model: Model to use (sonnet, haiku, opus).
            timeout: Max seconds before killing the process.
            role: 'mycelium' or 'user' — for token tracking.
            max_turns: Max agentic turns (0 = unlimited).
        """
        # bypassPermissions is required because .claude/ paths are protected
        # at the system level — Claude Code blocks writes to its own config
        # directory even when project settings allow it. In interactive mode,
        # users approve these writes manually. In headless -p mode, there's no
        # human to approve, so we bypass. This simulates the user clicking
        # "approve" — it does NOT modify the framework itself.
        cmd = [
            "claude", "-p", prompt,
            "--model", model,
            "--output-format", "json",
            "--dangerously-skip-permissions",
        ]

        if max_turns > 0:
            cmd.extend(["--max-turns", str(max_turns)])

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

        # Parse JSON output to extract text and token usage
        text_content = stdout
        is_error = False
        try:
            parsed = json.loads(stdout)
            text_content = parsed.get("result", stdout)
            is_error = parsed.get("is_error", False)
            usage = parsed.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            if role == "mycelium":
                self.token_tracker.mycelium_agent += tokens
            else:
                self.token_tracker.user_simulator += tokens
        except (json.JSONDecodeError, TypeError, AttributeError):
            # Backward compat: treat stdout as plain text if not valid JSON
            text_content = stdout

        if is_error:
            # Surface the error clearly — don't silently continue with empty output
            text_content = f"[CLAUDE_ERROR] {text_content}"

        return RunResult(
            stdout=text_content,
            stderr=stderr,
            exit_code=exit_code,
            duration_seconds=round(duration, 2),
            timed_out=timed_out,
        )
