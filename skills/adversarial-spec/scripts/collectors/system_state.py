"""
System State Collector

Collects build status, schema files, and directory trees.
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.process_runner import ProcessRunner, ProcessResult
from pre_gauntlet.models import (
    BuildStatus,
    Concern,
    ConcernCategory,
    ConcernSeverity,
    DirectoryTree,
    EvidenceRef,
    EvidenceType,
    FileSnapshot,
    SystemState,
    ValidationCommand,
    ValidationResult,
)


class SystemStateCollector:
    """Collects system state including build status, schemas, and trees."""

    def __init__(
        self,
        repo_root: str | Path,
        build_command: list[str] | None = None,
        build_timeout: int = 60,
        validation_commands: list[ValidationCommand] | None = None,
        schema_files: list[str] | None = None,
        critical_paths: list[str] | None = None,
        file_max_bytes: int = 200_000,
        tree_max_depth: int = 6,
        tree_max_entries: int = 5000,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.build_command = build_command
        self.build_timeout = build_timeout
        self.validation_commands = validation_commands or []
        self.schema_files = schema_files or []
        self.critical_paths = critical_paths or []
        self.file_max_bytes = file_max_bytes
        self.tree_max_depth = tree_max_depth
        self.tree_max_entries = tree_max_entries

        self.runner = ProcessRunner(repo_root, default_timeout=build_timeout)

    def collect(self) -> tuple[SystemState, list[Concern]]:
        """Collect system state and generate concerns.

        Returns: (SystemState, list of Concern)
        """
        concerns: list[Concern] = []
        collection_time = datetime.now()

        # Run build command
        build_status, build_exit, build_duration, build_output = self._run_build()
        if build_status in (BuildStatus.FAIL, BuildStatus.TIMEOUT):
            concerns.append(self._make_build_concern(build_status, build_output))

        # Run validation commands (schema/data consistency checks)
        validation_results, validation_concerns = self._run_validations()
        concerns.extend(validation_concerns)

        # Read schema files
        schema_contents, schema_concerns = self._read_schema_files()
        concerns.extend(schema_concerns)

        # Generate directory trees
        directory_trees = self._generate_trees()

        # Check working tree (via git status - reuse info)
        working_clean = self._check_working_tree()

        state = SystemState(
            build_status=build_status,
            build_exit_code=build_exit,
            build_duration_ms=build_duration,
            build_output_excerpt=build_output,
            validation_results=validation_results,
            schema_contents=schema_contents,
            directory_trees=directory_trees,
            working_tree_clean=working_clean,
            collection_timestamp=collection_time,
        )

        return state, concerns

    def _run_build(self) -> tuple[BuildStatus, int | None, int, str]:
        """Run the build command.

        Returns: (status, exit_code, duration_ms, output)
        """
        if not self.build_command:
            return BuildStatus.SKIP, None, 0, ""

        result = self.runner.run(self.build_command, timeout=self.build_timeout)

        if result.timed_out:
            return BuildStatus.TIMEOUT, None, result.duration_ms, result.stderr

        if result.success:
            return BuildStatus.PASS, result.exit_code, result.duration_ms, ""

        # Build failed - combine stdout and stderr
        output = result.stdout
        if result.stderr:
            output = f"{output}\n{result.stderr}" if output else result.stderr

        return BuildStatus.FAIL, result.exit_code, result.duration_ms, output

    def _make_build_concern(self, status: BuildStatus, output: str) -> Concern:
        """Create a concern for build failure."""
        if status == BuildStatus.TIMEOUT:
            return Concern(
                id=self._make_id("BUILD_TIMEOUT"),
                severity=ConcernSeverity.BLOCKER,
                category=ConcernCategory.BUILD,
                title="Build Command Timed Out",
                message=(
                    f"Build command `{' '.join(self.build_command or [])}` "
                    f"timed out after {self.build_timeout}s. "
                    "Baseline health cannot be verified."
                ),
                evidence_refs=[
                    EvidenceRef(
                        type=EvidenceType.COMMAND_OUTPUT,
                        source=" ".join(self.build_command or []),
                        excerpt=f"Timeout after {self.build_timeout}s",
                    )
                ],
            )

        # Truncate output for display
        output_excerpt = output[:2000] if len(output) > 2000 else output

        return Concern(
            id=self._make_id("BUILD_FAILURE"),
            severity=ConcernSeverity.BLOCKER,
            category=ConcernCategory.BUILD,
            title="Baseline Build Fails",
            message=(
                f"Build command `{' '.join(self.build_command or [])}` failed. "
                "The codebase cannot be deployed in its current state. "
                "This blocks ALL implementation work.\n\n"
                f"Output:\n```\n{output_excerpt}\n```"
            ),
            evidence_refs=[
                EvidenceRef(
                    type=EvidenceType.COMMAND_OUTPUT,
                    source=" ".join(self.build_command or []),
                    excerpt=output_excerpt,
                )
            ],
        )

    def _run_validations(self) -> tuple[list[ValidationResult], list[Concern]]:
        """Run validation commands and generate concerns for failures.

        Returns: (list of ValidationResult, list of Concern)
        """
        results = []
        concerns = []

        for val_cmd in self.validation_commands:
            result = self.runner.run(val_cmd.command, timeout=val_cmd.timeout_seconds)

            # Determine status
            if result.timed_out:
                status = BuildStatus.TIMEOUT
            elif result.success:
                status = BuildStatus.PASS
            else:
                status = BuildStatus.FAIL

            # Combine output
            output = result.stdout
            if result.stderr:
                output = f"{output}\n{result.stderr}" if output else result.stderr
            output_excerpt = output[:2000] if len(output) > 2000 else output

            val_result = ValidationResult(
                name=val_cmd.name,
                command=val_cmd.command,
                status=status,
                exit_code=result.exit_code if not result.timed_out else None,
                duration_ms=result.duration_ms,
                output_excerpt=output_excerpt,
                description=val_cmd.description,
            )
            results.append(val_result)

            # Generate concern if failed
            if status in (BuildStatus.FAIL, BuildStatus.TIMEOUT):
                concerns.append(self._make_validation_concern(val_cmd, val_result))

        return results, concerns

    def _make_validation_concern(
        self, cmd: ValidationCommand, result: ValidationResult
    ) -> Concern:
        """Create a concern for validation failure."""
        cmd_str = " ".join(cmd.command)

        if result.status == BuildStatus.TIMEOUT:
            return Concern(
                id=self._make_id(f"VALIDATION_TIMEOUT_{cmd.name}"),
                severity=ConcernSeverity.BLOCKER,
                category=ConcernCategory.SCHEMA,
                title=f"Validation Timed Out: {cmd.name}",
                message=(
                    f"Validation command `{cmd_str}` timed out after {cmd.timeout_seconds}s.\n"
                    f"Description: {cmd.description or 'Schema/data validation'}"
                ),
                evidence_refs=[
                    EvidenceRef(
                        type=EvidenceType.COMMAND_OUTPUT,
                        source=cmd_str,
                        excerpt=f"Timeout after {cmd.timeout_seconds}s",
                    )
                ],
            )

        # Validation failed
        return Concern(
            id=self._make_id(f"VALIDATION_FAILED_{cmd.name}"),
            severity=ConcernSeverity.BLOCKER,
            category=ConcernCategory.SCHEMA,
            title=f"Validation Failed: {cmd.name}",
            message=(
                f"Validation command `{cmd_str}` failed.\n"
                f"Description: {cmd.description or 'Schema/data validation'}\n\n"
                "This indicates schema/data drift - the schema definition does not match "
                "the actual data state. This must be resolved before implementation.\n\n"
                f"Output:\n```\n{result.output_excerpt}\n```"
            ),
            evidence_refs=[
                EvidenceRef(
                    type=EvidenceType.COMMAND_OUTPUT,
                    source=cmd_str,
                    excerpt=result.output_excerpt,
                )
            ],
        )

    def _read_schema_files(self) -> tuple[list[FileSnapshot], list[Concern]]:
        """Read schema files and generate concerns for missing ones.

        Returns: (list of FileSnapshot, list of Concern)
        """
        snapshots = []
        concerns = []

        for schema_path in self.schema_files:
            full_path = self.repo_root / schema_path

            if not full_path.exists():
                concerns.append(
                    Concern(
                        id=self._make_id(f"SCHEMA_MISSING_{schema_path}"),
                        severity=ConcernSeverity.BLOCKER,
                        category=ConcernCategory.SCHEMA,
                        title=f"Schema File Missing: {schema_path}",
                        message=(
                            f"Required schema file `{schema_path}` does not exist. "
                            "Cannot verify schema compatibility."
                        ),
                        evidence_refs=[
                            EvidenceRef(
                                type=EvidenceType.FILE_CONTENT,
                                source=schema_path,
                                excerpt="File not found",
                            )
                        ],
                    )
                )
                continue

            try:
                content = full_path.read_text()
                truncated = False

                if len(content) > self.file_max_bytes:
                    content = content[: self.file_max_bytes]
                    truncated = True

                # Calculate SHA256
                sha = hashlib.sha256(full_path.read_bytes()).hexdigest()

                snapshots.append(
                    FileSnapshot(
                        path=schema_path,
                        sha256=sha,
                        content=content,
                        truncated=truncated,
                    )
                )

            except Exception as e:
                concerns.append(
                    Concern(
                        id=self._make_id(f"SCHEMA_READ_ERROR_{schema_path}"),
                        severity=ConcernSeverity.WARN,
                        category=ConcernCategory.SCHEMA,
                        title=f"Schema File Unreadable: {schema_path}",
                        message=f"Could not read schema file `{schema_path}`: {e}",
                        evidence_refs=[
                            EvidenceRef(
                                type=EvidenceType.FILE_CONTENT,
                                source=schema_path,
                                excerpt=str(e),
                            )
                        ],
                    )
                )

        return snapshots, concerns

    def _generate_trees(self) -> list[DirectoryTree]:
        """Generate directory trees for critical paths."""
        trees = []

        for path in self.critical_paths:
            full_path = self.repo_root / path

            if not full_path.exists():
                continue

            tree_output, truncated = self._generate_tree(full_path)
            trees.append(
                DirectoryTree(
                    path=path,
                    tree=tree_output,
                    truncated=truncated,
                )
            )

        return trees

    def _generate_tree(self, path: Path, prefix: str = "", depth: int = 0) -> tuple[str, bool]:
        """Generate a tree structure for a directory.

        Returns: (tree_string, was_truncated)
        """
        if depth >= self.tree_max_depth:
            return f"{prefix}... [max depth reached]\n", True

        lines = []
        truncated = False
        entries = 0

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return f"{prefix}[permission denied]\n", False

        for i, item in enumerate(items):
            entries += 1
            if entries > self.tree_max_entries:
                lines.append(f"{prefix}... [{len(items) - i} more entries]\n")
                truncated = True
                break

            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{item.name}\n")

            if item.is_dir():
                extension = "    " if is_last else "│   "
                subtree, sub_truncated = self._generate_tree(
                    item, prefix + extension, depth + 1
                )
                lines.append(subtree)
                truncated = truncated or sub_truncated

        return "".join(lines), truncated

    def _check_working_tree(self) -> bool:
        """Check if working tree is clean via git status."""
        result = self.runner.run(["git", "status", "--porcelain"], validate=False)
        return result.success and len(result.stdout.strip()) == 0

    def _make_id(self, suffix: str) -> str:
        """Generate a concern ID."""
        content = f"{suffix}:{self.repo_root}"
        hash_val = hashlib.sha1(content.encode()).hexdigest()[:8]
        return f"COMP-{hash_val}"
