"""
Process Runner

Safe command execution with timeout, redaction, and security validation.
Shell=False only, argument arrays only.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


# Patterns that indicate potential secrets (high-entropy tokens)
SECRET_PATTERNS = [
    r"[A-Za-z0-9+/]{40,}={0,2}",  # Base64 tokens
    r"[a-f0-9]{32,}",  # Hex tokens (API keys, hashes)
    r"sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
    r"ghp_[a-zA-Z0-9]{36}",  # GitHub tokens
    r"gho_[a-zA-Z0-9]{36}",  # GitHub OAuth tokens
    r"xox[baprs]-[a-zA-Z0-9-]+",  # Slack tokens
    r"AIza[a-zA-Z0-9_-]{35}",  # Google API keys
    r"ya29\.[a-zA-Z0-9_-]+",  # Google OAuth tokens
]

# Dangerous shell metacharacters
DANGEROUS_CHARS = [";", "&&", "||", "|", "`", "$", "\n", "\r"]


@dataclass
class ProcessResult:
    """Result of a process execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


class ProcessRunnerError(Exception):
    """Error in process execution."""

    pass


class CommandValidationError(ProcessRunnerError):
    """Command failed security validation."""

    pass


def validate_command(command: list[str]) -> None:
    """Validate a command for security issues.

    Raises CommandValidationError if the command is unsafe.
    """
    if not command:
        raise CommandValidationError("Empty command")

    for i, arg in enumerate(command):
        for char in DANGEROUS_CHARS:
            if char in arg:
                raise CommandValidationError(
                    f"Dangerous character '{repr(char)}' in argument {i}: {arg[:50]}"
                )


def redact_secrets(text: str, extra_patterns: list[str] | None = None) -> str:
    """Redact potential secrets from text.

    Args:
        text: Text to redact
        extra_patterns: Additional regex patterns to redact

    Returns:
        Text with secrets replaced by ***REDACTED***
    """
    patterns = SECRET_PATTERNS.copy()
    if extra_patterns:
        patterns.extend(extra_patterns)

    result = text
    for pattern in patterns:
        result = re.sub(pattern, "***REDACTED***", result)

    return result


def truncate_output(text: str, max_lines: int = 500, max_chars: int = 50000) -> tuple[str, bool]:
    """Truncate output to reasonable size.

    Returns: (truncated_text, was_truncated)
    """
    truncated = False

    # Truncate by characters first
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    # Then by lines
    lines = text.split("\n")
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    result = "\n".join(lines)
    if truncated:
        result += "\n... [TRUNCATED]"

    return result, truncated


class ProcessRunner:
    """Safe process runner with timeout and redaction."""

    def __init__(
        self,
        cwd: str | Path,
        default_timeout: int = 60,
        redact_output: bool = True,
        extra_redact_patterns: list[str] | None = None,
    ):
        self.cwd = Path(cwd).resolve()
        self.default_timeout = default_timeout
        self.redact_output = redact_output
        self.extra_redact_patterns = extra_redact_patterns or []

        if not self.cwd.is_dir():
            raise ProcessRunnerError(f"Working directory does not exist: {self.cwd}")

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        validate: bool = True,
    ) -> ProcessResult:
        """Run a command safely.

        Args:
            command: Command as argument array (NO shell=True)
            timeout: Timeout in seconds (default: self.default_timeout)
            validate: Whether to validate command for dangerous chars

        Returns:
            ProcessResult with output and timing

        Raises:
            CommandValidationError: If command fails validation
            ProcessRunnerError: If execution fails
        """
        if validate:
            validate_command(command)

        timeout = timeout or self.default_timeout
        start_time = time.monotonic()

        try:
            result = subprocess.run(
                command,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # NEVER shell=True
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            stdout = result.stdout
            stderr = result.stderr

            # Redact secrets
            if self.redact_output:
                stdout = redact_secrets(stdout, self.extra_redact_patterns)
                stderr = redact_secrets(stderr, self.extra_redact_patterns)

            # Truncate
            stdout, _ = truncate_output(stdout)
            stderr, _ = truncate_output(stderr)

            return ProcessResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                timed_out=False,
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                duration_ms=duration_ms,
                timed_out=True,
            )

        except FileNotFoundError:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=f"Command not found: {command[0]}",
                duration_ms=duration_ms,
                timed_out=False,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            return ProcessResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                timed_out=False,
            )
