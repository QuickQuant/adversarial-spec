"""
Execution Planner - Gauntlet concern parsing and linking.

Most of this package was deprecated in Feb 2026 (Option B+ decision).
Generation logic moved to LLM guidelines in phases/06-execution.md.
Only gauntlet concern parsing remains as code.
"""

from execution_planner.gauntlet_concerns import (
    GauntletConcern,
    GauntletConcernParser,
    GauntletReport,
    LinkedConcern,
    load_concerns_for_spec,
)

__all__ = [
    "GauntletConcern",
    "GauntletConcernParser",
    "GauntletReport",
    "LinkedConcern",
    "load_concerns_for_spec",
]
