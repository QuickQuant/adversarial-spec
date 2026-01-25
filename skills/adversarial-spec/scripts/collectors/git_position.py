"""
Git Position Collector

Collects git repository position and staleness information.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.git_cli import GitCli, GitCliError
from pre_gauntlet.models import (
    CommitSummary,
    Concern,
    ConcernCategory,
    ConcernSeverity,
    EvidenceRef,
    EvidenceType,
    FileChange,
    FileChangeStatus,
    GitPosition,
)


class GitPositionCollector:
    """Collects git position and generates staleness concerns."""

    def __init__(
        self,
        repo_root: str | Path,
        base_branch: str = "main",
        staleness_threshold_days: int = 3,
        spec_affected_files: list[str] | None = None,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.base_branch = base_branch
        self.staleness_threshold_days = staleness_threshold_days
        self.spec_affected_files = set(spec_affected_files or [])

        self.git = GitCli(repo_root)

    def collect(self) -> tuple[GitPosition, list[Concern]]:
        """Collect git position and generate concerns.

        Returns: (GitPosition, list of Concern)
        """
        concerns: list[Concern] = []

        # Check if base branch exists
        if not self.git.branch_exists(self.base_branch):
            raise GitCliError(f"Base branch '{self.base_branch}' does not exist")

        # Get basic position info
        current_branch = self.git.get_current_branch()
        head_commit = self.git.get_head_commit()
        base_commit = self.git.get_branch_commit(self.base_branch)
        merge_base = self.git.get_merge_base(self.base_branch)
        detached = self.git.is_detached_head()
        working_clean = self.git.is_working_tree_clean()

        # Get ahead/behind counts
        commits_ahead, commits_behind = self.git.get_commits_ahead_behind(self.base_branch)

        # Get merge base date
        last_sync = self.git.get_commit_date(merge_base)

        # Get recent commits on base branch
        recent_commits_raw = self.git.get_recent_commits(self.base_branch, count=10)
        recent_commits = [
            CommitSummary(
                hash=c["hash"],
                author=c["author"],
                date=c["date"],
                subject=c["subject"],
            )
            for c in recent_commits_raw
        ]

        # Get changed files
        changed_files_raw = self.git.get_changed_files(self.base_branch)
        all_changed = [
            FileChange(
                path=f["path"],
                status=FileChangeStatus(f["status"]),
            )
            for f in changed_files_raw
        ]

        # Filter to spec-affected files
        affected_changes = []
        if self.spec_affected_files:
            for fc in all_changed:
                if fc.path in self.spec_affected_files:
                    affected_changes.append(fc)

        # Build position object
        position = GitPosition(
            current_branch=current_branch,
            head_commit=head_commit,
            base_branch=self.base_branch,
            base_commit=base_commit,
            merge_base_commit=merge_base,
            commits_ahead=commits_ahead,
            commits_behind=commits_behind,
            last_sync_with_base=last_sync,
            main_recent_commits=recent_commits,
            affected_files_changes=affected_changes,
            working_tree_clean=working_clean,
            detached_head=detached,
        )

        # Generate concerns
        concerns.extend(self._generate_concerns(position))

        return position, concerns

    def _generate_concerns(self, position: GitPosition) -> list[Concern]:
        """Generate concerns based on git position."""
        concerns = []

        # Detached HEAD warning
        if position.detached_head:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_DETACHED"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title="Detached HEAD State",
                    message=(
                        "Repository is in detached HEAD state. "
                        "Commits may not be associated with a branch."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source="git rev-parse --abbrev-ref HEAD",
                            excerpt="HEAD",
                        )
                    ],
                )
            )

        # Commits behind warning
        if position.commits_behind > 0:
            # Get commit subjects for evidence
            commit_subjects = "\n".join(
                f"  - {c.hash[:7]}: {c.subject}"
                for c in position.main_recent_commits[:position.commits_behind]
            )

            concerns.append(
                Concern(
                    id=self._make_id("GIT_STALE"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title=f"Branch Behind {position.base_branch}",
                    message=(
                        f"Current branch is {position.commits_behind} commit(s) behind "
                        f"{position.base_branch}. Recent commits:\n{commit_subjects}"
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git rev-list --count {position.base_branch}...HEAD",
                            excerpt=f"{position.commits_behind} commits behind",
                        )
                    ],
                )
            )

        # Staleness time warning
        # Handle timezone-aware vs naive datetime comparison
        now = datetime.now(position.last_sync_with_base.tzinfo) if position.last_sync_with_base.tzinfo else datetime.now()
        days_since_sync = (now - position.last_sync_with_base).days
        if days_since_sync > self.staleness_threshold_days:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_STALE_TIME"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title=f"Branch Stale ({days_since_sync} days)",
                    message=(
                        f"Last sync with {position.base_branch} was {days_since_sync} days ago "
                        f"(threshold: {self.staleness_threshold_days} days). "
                        "Consider rebasing to get latest changes."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git merge-base HEAD {position.base_branch}",
                            excerpt=position.last_sync_with_base.isoformat(),
                        )
                    ],
                )
            )

        # Affected files changed - BLOCKER
        if position.affected_files_changes:
            file_list = "\n".join(
                f"  - {fc.path} ({fc.status.value})"
                for fc in position.affected_files_changes
            )
            concerns.append(
                Concern(
                    id=self._make_id("GIT_AFFECTED_FILES_CHANGED"),
                    severity=ConcernSeverity.BLOCKER,
                    category=ConcernCategory.GIT,
                    title="Spec-Affected Files Changed on Base Branch",
                    message=(
                        f"Files referenced by the spec have changed on {position.base_branch} "
                        f"since this branch diverged:\n{file_list}\n\n"
                        "The spec may be based on stale understanding. ALIGNMENT MODE required."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source=f"git diff --name-status {position.base_branch}...HEAD",
                            excerpt=file_list,
                        )
                    ],
                )
            )

        # Dirty working tree warning
        if not position.working_tree_clean:
            concerns.append(
                Concern(
                    id=self._make_id("GIT_DIRTY"),
                    severity=ConcernSeverity.WARN,
                    category=ConcernCategory.GIT,
                    title="Uncommitted Changes",
                    message=(
                        "Working tree has uncommitted changes. "
                        "Baseline verification may not reflect committed state."
                    ),
                    evidence_refs=[
                        EvidenceRef(
                            type=EvidenceType.GIT_LOG,
                            source="git status --porcelain",
                            excerpt="(non-empty output)",
                        )
                    ],
                )
            )

        return concerns

    def _make_id(self, suffix: str) -> str:
        """Generate a concern ID."""
        import hashlib
        content = f"{suffix}:{self.base_branch}:{self.repo_root}"
        hash_val = hashlib.sha1(content.encode()).hexdigest()[:8]
        return f"COMP-{hash_val}"
