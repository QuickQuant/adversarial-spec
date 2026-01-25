"""
Extractors Module

Extract information from spec documents.
"""

from .spec_affected_files import SpecAffectedFilesExtractor, extract_spec_affected_files

__all__ = [
    "SpecAffectedFilesExtractor",
    "extract_spec_affected_files",
]
