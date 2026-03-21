"""Regression tests for the gauntlet package public surface."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_gauntlet_shim_exports_exact_public_surface():
    """Step 0 must expose only the documented public symbols."""
    import gauntlet

    expected_exports = [
        "ADVERSARIES",
        "format_gauntlet_report",
        "get_adversary_leaderboard",
        "get_medal_leaderboard",
        "run_gauntlet",
    ]

    assert gauntlet.__all__ == expected_exports
    assert isinstance(gauntlet.ADVERSARIES, dict)
    assert callable(gauntlet.format_gauntlet_report)
    assert callable(gauntlet.get_adversary_leaderboard)
    assert callable(gauntlet.get_medal_leaderboard)
    assert callable(gauntlet.run_gauntlet)
