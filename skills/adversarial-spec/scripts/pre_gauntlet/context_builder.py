"""
Context Builder

Builds the LLM context markdown from collected data.
"""

from __future__ import annotations

from datetime import datetime

from .models import (
    BuildStatus,
    ConcernSeverity,
    GitPosition,
    PreGauntletResult,
    SystemState,
)


class ContextBuilder:
    """Builds LLM context markdown from pre-gauntlet data."""

    def __init__(self, max_chars: int = 200_000):
        self.max_chars = max_chars
        self.truncated_sections: list[str] = []

    def build(
        self,
        git_position: GitPosition | None,
        system_state: SystemState | None,
        spec_text: str,
    ) -> str:
        """Build the context markdown.

        Args:
            git_position: Git position data (optional)
            system_state: System state data (optional)
            spec_text: The specification text

        Returns:
            Formatted markdown context
        """
        sections = []

        # Header
        sections.append("# SYSTEM CONTEXT (GROUND TRUTH)")
        sections.append("")
        sections.append(
            "Trust this section over any assumptions. "
            "If the spec contradicts this, raise a COMP concern."
        )
        sections.append("")

        # Git Position
        if git_position:
            sections.append(self._build_git_section(git_position))

        # Baseline Health
        if system_state:
            sections.append(self._build_health_section(system_state))

        # Schema Snapshots
        if system_state and system_state.schema_contents:
            sections.append(self._build_schema_section(system_state))

        # Directory Trees
        if system_state and system_state.directory_trees:
            sections.append(self._build_tree_section(system_state))

        # Proposed Spec
        sections.append("## 5. Proposed Spec")
        sections.append("")
        sections.append(spec_text)

        # Join and truncate if needed
        result = "\n".join(sections)
        result = self._truncate_if_needed(result)

        return result

    def _build_git_section(self, pos: GitPosition) -> str:
        """Build the git position section."""
        lines = ["## 1. Git Position", ""]

        # Basic info
        lines.append(f"- Branch: {pos.current_branch} ({pos.commits_ahead} ahead, {pos.commits_behind} behind {pos.base_branch})")
        lines.append(f"- Head: {pos.head_commit[:12]}")

        # Last sync
        now = datetime.now(pos.last_sync_with_base.tzinfo) if pos.last_sync_with_base.tzinfo else datetime.now()
        days_ago = (now - pos.last_sync_with_base).days
        lines.append(f"- Last sync with {pos.base_branch}: {pos.last_sync_with_base.date()} ({days_ago} days ago)")

        # Working tree
        clean_status = "CLEAN" if pos.working_tree_clean else "DIRTY (uncommitted changes)"
        lines.append(f"- Working tree: {clean_status}")

        # Detached HEAD warning
        if pos.detached_head:
            lines.append("- WARNING: Detached HEAD state")

        # Recent commits on base if behind
        if pos.commits_behind > 0 and pos.main_recent_commits:
            lines.append("")
            lines.append(f"WARNING: {pos.base_branch} has {pos.commits_behind} new commit(s) since this branch diverged:")
            for commit in pos.main_recent_commits[: pos.commits_behind]:
                lines.append(f"  - {commit.hash[:7]}: \"{commit.subject}\"")

        # Affected files changed
        if pos.affected_files_changes:
            lines.append("")
            lines.append("CRITICAL: Spec-affected files have changed on base branch:")
            for fc in pos.affected_files_changes:
                lines.append(f"  - {fc.path} ({fc.status.value})")

        lines.append("")
        return "\n".join(lines)

    def _build_health_section(self, state: SystemState) -> str:
        """Build the baseline health section."""
        lines = ["## 2. Baseline Health", ""]

        status_str = state.build_status.value
        lines.append(f"- Build Status: {status_str}")

        if state.build_exit_code is not None:
            lines.append(f"- Exit Code: {state.build_exit_code}")

        if state.build_duration_ms > 0:
            lines.append(f"- Duration: {state.build_duration_ms}ms")

        if state.build_output_excerpt:
            lines.append("- Output (redacted):")
            lines.append("```")
            lines.append(state.build_output_excerpt)
            lines.append("```")

        # Validation results
        if state.validation_results:
            lines.append("")
            lines.append("### Validation Checks")
            for val in state.validation_results:
                status_icon = "PASS" if val.status.value == "PASS" else "FAIL"
                lines.append(f"- **{val.name}**: {status_icon}")
                if val.description:
                    lines.append(f"  - {val.description}")
                if val.status.value != "PASS" and val.output_excerpt:
                    lines.append("  - Output:")
                    lines.append("  ```")
                    for line in val.output_excerpt.split("\n")[:10]:  # First 10 lines
                        lines.append(f"  {line}")
                    lines.append("  ```")

        lines.append("")
        return "\n".join(lines)

    def _build_schema_section(self, state: SystemState) -> str:
        """Build the schema snapshots section."""
        lines = ["## 3. Schema Snapshots", ""]

        for snapshot in state.schema_contents:
            lines.append(f"### {snapshot.path} (sha256: {snapshot.sha256[:16]}...)")
            if snapshot.truncated:
                lines.append("*[TRUNCATED]*")
            lines.append("```")
            lines.append(snapshot.content)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _build_tree_section(self, state: SystemState) -> str:
        """Build the directory trees section."""
        lines = ["## 4. Directory Trees", ""]

        for tree in state.directory_trees:
            lines.append(f"### {tree.path}")
            if tree.truncated:
                lines.append("*[TRUNCATED]*")
            lines.append("```")
            lines.append(tree.tree)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def _truncate_if_needed(self, text: str) -> str:
        """Truncate text if it exceeds max_chars."""
        if len(text) <= self.max_chars:
            return text

        # Truncate from end, preserving structure
        truncated = text[: self.max_chars]

        # Find last complete section
        last_section = truncated.rfind("\n## ")
        if last_section > self.max_chars // 2:
            truncated = truncated[:last_section]

        truncated += "\n\n... [CONTEXT TRUNCATED DUE TO SIZE]"
        self.truncated_sections.append("FULL_CONTEXT")

        return truncated


def build_context(
    git_position: GitPosition | None,
    system_state: SystemState | None,
    spec_text: str,
    max_chars: int = 200_000,
) -> tuple[str, list[str]]:
    """Convenience function to build context.

    Returns: (context_markdown, truncated_sections)
    """
    builder = ContextBuilder(max_chars=max_chars)
    context = builder.build(git_position, system_state, spec_text)
    return context, builder.truncated_sections
