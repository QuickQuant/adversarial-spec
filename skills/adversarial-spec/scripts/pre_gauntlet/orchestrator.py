"""
Pre-Gauntlet Orchestrator

Entry point for pre-gauntlet execution. Coordinates collectors, extractors,
context building, and alignment mode.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.git_position import GitPositionCollector
from collectors.system_state import SystemStateCollector
from extractors.spec_affected_files import extract_spec_affected_files
from integrations.git_cli import GitCliError

from .alignment_mode import run_alignment_mode
from .context_builder import build_context
from .models import (
    CompatibilityConfig,
    ConcernSeverity,
    ContextSummary,
    DocType,
    PreGauntletResult,
    PreGauntletStatus,
    Timings,
)


class PreGauntletOrchestrator:
    """Orchestrates pre-gauntlet execution."""

    def __init__(
        self,
        repo_root: str | Path,
        config: CompatibilityConfig,
        interactive: bool = True,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.config = config
        self.interactive = interactive

    def run(
        self,
        spec_text: str,
        doc_type: DocType,
    ) -> PreGauntletResult:
        """Run pre-gauntlet checks.

        Args:
            spec_text: The specification document text
            doc_type: Type of document (prd, tech, debug)

        Returns:
            PreGauntletResult with status, concerns, and context
        """
        start_time = time.monotonic()
        timings = Timings()

        # Get doc type rules
        rules = self.config.get_doc_type_rule(doc_type)

        # Check if pre-gauntlet is enabled for this doc type
        if not self.config.enabled or not rules.enabled:
            return PreGauntletResult(
                status=PreGauntletStatus.COMPLETE,
                doc_type=doc_type,
                context_markdown=spec_text,  # Just pass through the spec
            )

        all_concerns = []
        git_position = None
        system_state = None

        # Extract spec-affected files
        try:
            spec_affected_files = extract_spec_affected_files(
                spec_text=spec_text,
                repo_root=self.repo_root,
                include_untracked=self.config.include_untracked,
                critical_paths=self.config.critical_paths,
            )
        except Exception as e:
            print(f"Warning: Could not extract spec-affected files: {e}", file=sys.stderr)
            spec_affected_files = []

        # Collect git position
        if rules.require_git:
            git_start = time.monotonic()
            try:
                collector = GitPositionCollector(
                    repo_root=self.repo_root,
                    base_branch=self.config.base_branch,
                    staleness_threshold_days=self.config.staleness_threshold_days,
                    spec_affected_files=spec_affected_files,
                )
                git_position, git_concerns = collector.collect()
                all_concerns.extend(git_concerns)
            except GitCliError as e:
                return PreGauntletResult(
                    status=PreGauntletStatus.INFRA_ERROR,
                    doc_type=doc_type,
                    context_markdown=f"Git error: {e}",
                )
            timings.git_ms = int((time.monotonic() - git_start) * 1000)

        # Collect system state
        if rules.require_build or rules.require_schema or rules.require_trees:
            state_start = time.monotonic()
            try:
                collector = SystemStateCollector(
                    repo_root=self.repo_root,
                    build_command=self.config.build_command if rules.require_build else None,
                    build_timeout=self.config.build_timeout_seconds,
                    schema_files=self.config.schema_files if rules.require_schema else None,
                    critical_paths=self.config.critical_paths if rules.require_trees else None,
                    file_max_bytes=self.config.file_max_bytes,
                    tree_max_depth=self.config.tree_max_depth,
                    tree_max_entries=self.config.tree_max_entries,
                )
                system_state, state_concerns = collector.collect()
                all_concerns.extend(state_concerns)

                timings.build_ms = system_state.build_duration_ms
                timings.files_ms = int((time.monotonic() - state_start) * 1000) - timings.build_ms

            except Exception as e:
                return PreGauntletResult(
                    status=PreGauntletStatus.INFRA_ERROR,
                    doc_type=doc_type,
                    context_markdown=f"System state collection error: {e}",
                )

        # Build context
        context_markdown, truncated_sections = build_context(
            git_position=git_position,
            system_state=system_state,
            spec_text=spec_text,
            max_chars=self.config.context_max_chars,
        )

        # Calculate total time
        timings.total_ms = int((time.monotonic() - start_time) * 1000)

        # Build initial result
        result = PreGauntletResult(
            status=PreGauntletStatus.COMPLETE,
            doc_type=doc_type,
            concerns=all_concerns,
            git_position=git_position,
            system_state=system_state,
            context_summary=ContextSummary(
                context_chars=len(context_markdown),
                truncated_sections=truncated_sections,
            ),
            timings=timings,
            context_markdown=context_markdown,
        )

        # Check for blockers and run alignment mode if needed
        blockers = result.get_blockers()
        if blockers:
            status, alignment_issues, was_overridden = run_alignment_mode(
                blockers=blockers,
                result=result,
                interactive=self.interactive,
            )
            result.status = status
            result.alignment_issues = alignment_issues
            result.alignment_override = was_overridden

        return result


def run_pre_gauntlet(
    spec_text: str,
    doc_type: DocType | str,
    repo_root: str | Path | None = None,
    config: CompatibilityConfig | None = None,
    interactive: bool = True,
) -> PreGauntletResult:
    """Run pre-gauntlet checks.

    Args:
        spec_text: The specification document text
        doc_type: Type of document (prd, tech, debug)
        repo_root: Path to repository root (default: current directory)
        config: Configuration (default: auto-load from pyproject.toml)
        interactive: Whether to run in interactive mode

    Returns:
        PreGauntletResult with status, concerns, and context
    """
    # Convert string to enum
    if isinstance(doc_type, str):
        doc_type = DocType(doc_type.lower())

    # Default repo root
    if repo_root is None:
        repo_root = Path.cwd()
    repo_root = Path(repo_root).resolve()

    # Load config from pyproject.toml if not provided
    if config is None:
        config = load_config_from_pyproject(repo_root)

    orchestrator = PreGauntletOrchestrator(
        repo_root=repo_root,
        config=config,
        interactive=interactive,
    )

    return orchestrator.run(spec_text=spec_text, doc_type=doc_type)


def load_config_from_pyproject(repo_root: Path) -> CompatibilityConfig:
    """Load configuration from pyproject.toml.

    Args:
        repo_root: Path to repository root

    Returns:
        CompatibilityConfig (defaults if not found)
    """
    pyproject_path = repo_root / "pyproject.toml"

    if not pyproject_path.exists():
        return CompatibilityConfig()

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            # No TOML parser available, use defaults
            return CompatibilityConfig()

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        tool_config = data.get("tool", {}).get("adversarial-spec", {}).get("compatibility", {})

        if not tool_config:
            return CompatibilityConfig()

        return CompatibilityConfig(**tool_config)

    except Exception as e:
        print(f"Warning: Could not parse pyproject.toml: {e}", file=sys.stderr)
        return CompatibilityConfig()


def save_report(result: PreGauntletResult, output_path: Path) -> None:
    """Save pre-gauntlet report to JSON file.

    Args:
        result: Pre-gauntlet result
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict, excluding the full context markdown
    report = result.model_dump(exclude={"context_markdown"})

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)


# Exit codes for CLI
EXIT_COMPLETE = 0
EXIT_NEEDS_ALIGNMENT = 2
EXIT_ABORTED = 3
EXIT_CONFIG_ERROR = 4
EXIT_INFRA_ERROR = 5


def get_exit_code(status: PreGauntletStatus) -> int:
    """Get CLI exit code for a status."""
    return {
        PreGauntletStatus.COMPLETE: EXIT_COMPLETE,
        PreGauntletStatus.NEEDS_ALIGNMENT: EXIT_NEEDS_ALIGNMENT,
        PreGauntletStatus.ABORTED: EXIT_ABORTED,
        PreGauntletStatus.CONFIG_ERROR: EXIT_CONFIG_ERROR,
        PreGauntletStatus.INFRA_ERROR: EXIT_INFRA_ERROR,
    }.get(status, 1)
