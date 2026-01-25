"""
Git CLI Integration

All git command execution and parsing. Read-only operations only.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class GitCommandResult:
    """Result of a git command execution."""

    success: bool
    stdout: str
    stderr: str
    return_code: int


class GitCliError(Exception):
    """Error executing git command."""

    def __init__(self, message: str, result: GitCommandResult | None = None):
        super().__init__(message)
        self.result = result


class GitCli:
    """Git command line interface wrapper. Read-only operations only."""

    def __init__(self, repo_root: str | Path, timeout: int = 30):
        self.repo_root = Path(repo_root).resolve()
        self.timeout = timeout

        # Verify git is available
        if not self._check_git_available():
            raise GitCliError("Git is not available in PATH")

        # Verify this is a git repository
        if not self._is_git_repo():
            raise GitCliError(f"Not a git repository: {self.repo_root}")

    def _check_git_available(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _is_git_repo(self) -> bool:
        """Check if repo_root is a git repository."""
        result = self._run(["rev-parse", "--git-dir"])
        return result.success

    def _run(self, args: list[str]) -> GitCommandResult:
        """Run a git command and return the result."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return GitCommandResult(
                success=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return GitCommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {self.timeout}s",
                return_code=-1,
            )

    def get_current_branch(self) -> str:
        """Get the current branch name, or 'HEAD' if detached."""
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        if not result.success:
            raise GitCliError("Failed to get current branch", result)
        return result.stdout

    def get_head_commit(self) -> str:
        """Get the HEAD commit hash."""
        result = self._run(["rev-parse", "HEAD"])
        if not result.success:
            raise GitCliError("Failed to get HEAD commit", result)
        return result.stdout

    def get_branch_commit(self, branch: str) -> str:
        """Get the commit hash for a branch."""
        result = self._run(["rev-parse", branch])
        if not result.success:
            raise GitCliError(f"Failed to get commit for branch '{branch}'", result)
        return result.stdout

    def get_merge_base(self, branch: str) -> str:
        """Get the merge base between HEAD and a branch."""
        result = self._run(["merge-base", "HEAD", branch])
        if not result.success:
            raise GitCliError(f"Failed to get merge base with '{branch}'", result)
        return result.stdout

    def get_commits_ahead_behind(self, base_branch: str) -> tuple[int, int]:
        """Get commits ahead and behind relative to base branch.

        Returns: (commits_ahead, commits_behind)
        """
        result = self._run(["rev-list", "--left-right", "--count", f"{base_branch}...HEAD"])
        if not result.success:
            raise GitCliError(f"Failed to get ahead/behind count for '{base_branch}'", result)

        parts = result.stdout.split()
        if len(parts) != 2:
            raise GitCliError(f"Unexpected output format: {result.stdout}", result)

        return int(parts[1]), int(parts[0])  # ahead, behind

    def get_recent_commits(self, branch: str, count: int = 10) -> list[dict]:
        """Get recent commits on a branch.

        Returns list of dicts with: hash, author, date, subject
        """
        # Format: hash|ISO date|author|subject
        result = self._run([
            "log",
            "-n", str(count),
            "--format=%H|%aI|%an|%s",
            branch,
        ])
        if not result.success:
            # Branch might not exist or have no commits
            return []

        commits = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0],
                    "date": datetime.fromisoformat(parts[1]),
                    "author": parts[2],
                    "subject": parts[3],
                })
        return commits

    def get_commit_date(self, commit: str) -> datetime:
        """Get the date of a commit."""
        result = self._run(["log", "-1", "--format=%aI", commit])
        if not result.success:
            raise GitCliError(f"Failed to get date for commit '{commit}'", result)
        return datetime.fromisoformat(result.stdout)

    def get_changed_files(self, base_branch: str) -> list[dict]:
        """Get files changed between base branch and HEAD.

        Returns list of dicts with: path, status (A/M/D/R)
        """
        result = self._run(["diff", "--name-status", f"{base_branch}...HEAD"])
        if not result.success:
            return []

        files = []
        for line in result.stdout.split("\n"):
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status = parts[0][0]  # First char (R100 -> R)
                path = parts[1]
                files.append({"path": path, "status": status})
        return files

    def is_working_tree_clean(self) -> bool:
        """Check if the working tree is clean (no uncommitted changes)."""
        result = self._run(["status", "--porcelain"])
        if not result.success:
            return False
        return len(result.stdout) == 0

    def is_detached_head(self) -> bool:
        """Check if HEAD is detached."""
        branch = self.get_current_branch()
        return branch == "HEAD"

    def list_files(self, include_untracked: bool = False) -> list[str]:
        """List all tracked files in the repository."""
        result = self._run(["ls-files"])
        if not result.success:
            return []

        files = [f for f in result.stdout.split("\n") if f.strip()]

        if include_untracked:
            untracked_result = self._run(["ls-files", "--others", "--exclude-standard"])
            if untracked_result.success:
                files.extend([f for f in untracked_result.stdout.split("\n") if f.strip()])

        return files

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists."""
        result = self._run(["rev-parse", "--verify", branch])
        return result.success
