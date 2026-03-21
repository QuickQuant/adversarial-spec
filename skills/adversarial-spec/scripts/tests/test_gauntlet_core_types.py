"""Contract tests for extracted gauntlet core types."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from gauntlet.core_types import (
    GauntletClusteringError,
    GauntletConfig,
    GauntletExecutionError,
    GauntletResult,
    SYNTHESIS_CATEGORIES,
    normalize_verdict,
)


def test_core_types_exports_step1_contract():
    """Step 1 must expose the new config/error types and concerns_path."""
    assert GauntletConfig is not None
    assert issubclass(GauntletClusteringError, Exception)
    assert issubclass(GauntletExecutionError, Exception)
    assert "concerns_path" in GauntletResult.__dataclass_fields__


def test_normalize_verdict_defaults_unknown_values_to_deferred():
    """Unknown verdicts should preserve the monolith fallback behavior."""
    assert normalize_verdict("dismiss") == "dismissed"
    assert normalize_verdict(" totally-new-value ") == "deferred"


def test_synthesis_categories_match_spec_order():
    """The synthesis taxonomy must stay aligned with the redesign spec."""
    assert SYNTHESIS_CATEGORIES == [
        "Correctness Bugs",
        "Race Conditions",
        "Failure Modes",
        "Security",
        "Operability",
        "Scalability",
        "Design Debt",
        "Underspecification",
    ]
