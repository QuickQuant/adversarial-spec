"""
Spec Affected Files Extractor

Parses spec text to identify file paths referenced in the spec.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.git_cli import GitCli


class SpecAffectedFilesExtractor:
    """Extracts file paths referenced in a spec document."""

    # Pattern to match file paths
    # Note: We filter out URLs in post-processing since variable-width lookbehind isn't supported
    FILE_PATH_PATTERN = re.compile(
        r"\b"  # Word boundary
        r"([a-zA-Z0-9_.-]+/)*"  # Optional directory parts
        r"[a-zA-Z0-9_.-]+"  # Filename
        r"\.[a-zA-Z0-9]+"  # Extension
        r"\b"  # Word boundary
    )

    # Pattern for directory references
    DIR_PATH_PATTERN = re.compile(
        r"\b"  # Word boundary
        r"([a-zA-Z0-9_.-]+/)+"  # One or more directory parts ending in /
    )

    # Pattern to detect URLs (for filtering)
    URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)

    def __init__(
        self,
        repo_root: str | Path,
        include_untracked: bool = False,
        critical_paths: list[str] | None = None,
        max_matches: int = 100,
    ):
        self.repo_root = Path(repo_root).resolve()
        self.include_untracked = include_untracked
        self.critical_paths = set(critical_paths or [])
        self.max_matches = max_matches

        self.git = GitCli(repo_root)
        self._file_index: set[str] | None = None

    def _build_file_index(self) -> set[str]:
        """Build index of files in the repository."""
        if self._file_index is not None:
            return self._file_index

        files = self.git.list_files(include_untracked=self.include_untracked)
        self._file_index = set(files)
        return self._file_index

    def extract(self, spec_text: str) -> list[str]:
        """Extract file paths from spec text.

        Args:
            spec_text: The specification document text

        Returns:
            List of file paths that exist in the repository
        """
        file_index = self._build_file_index()
        matches: set[str] = set()

        # Find all URLs to exclude
        url_spans = set()
        for match in self.URL_PATTERN.finditer(spec_text):
            url_spans.add((match.start(), match.end()))

        def is_in_url(start: int, end: int) -> bool:
            """Check if a span overlaps with any URL."""
            for url_start, url_end in url_spans:
                if start >= url_start and end <= url_end:
                    return True
            return False

        # Extract file path matches
        for match in self.FILE_PATH_PATTERN.finditer(spec_text):
            # Skip if inside a URL
            if is_in_url(match.start(), match.end()):
                continue

            path = match.group(0)
            # Skip email-like patterns
            if "@" in spec_text[max(0, match.start() - 1) : match.start()]:
                continue

            if self._is_valid_path(path, file_index):
                matches.add(path)

        # Extract directory matches and add all files under them
        for match in self.DIR_PATH_PATTERN.finditer(spec_text):
            dir_path = match.group(0)
            # Add files that start with this directory
            for file_path in file_index:
                if file_path.startswith(dir_path):
                    matches.add(file_path)

        # Add critical paths
        for critical_path in self.critical_paths:
            for file_path in file_index:
                if file_path.startswith(critical_path):
                    matches.add(file_path)

        # Sort for deterministic order and limit
        result = sorted(matches)[: self.max_matches]
        return result

    def _is_valid_path(self, path: str, file_index: set[str]) -> bool:
        """Check if a path is valid (exists in file index or critical paths)."""
        # Direct match in file index
        if path in file_index:
            return True

        # Check if it's under a critical path
        for critical in self.critical_paths:
            if path.startswith(critical):
                return True

        # Check with common variations
        variations = [
            path,
            f"./{path}",
            path.lstrip("./"),
        ]

        for var in variations:
            if var in file_index:
                return True

        return False


def extract_spec_affected_files(
    spec_text: str,
    repo_root: str | Path,
    include_untracked: bool = False,
    critical_paths: list[str] | None = None,
    max_matches: int = 100,
) -> list[str]:
    """Convenience function to extract affected files from spec.

    Args:
        spec_text: The specification document text
        repo_root: Path to the repository root
        include_untracked: Whether to include untracked files
        critical_paths: Additional paths to always include
        max_matches: Maximum number of file paths to return

    Returns:
        List of file paths referenced in the spec
    """
    extractor = SpecAffectedFilesExtractor(
        repo_root=repo_root,
        include_untracked=include_untracked,
        critical_paths=critical_paths,
        max_matches=max_matches,
    )
    return extractor.extract(spec_text)
