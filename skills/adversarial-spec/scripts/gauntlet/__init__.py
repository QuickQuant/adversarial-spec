"""Gauntlet package — adversarial spec evaluation pipeline.

Shim that re-exports the 5 public symbols from gauntlet_monolith
during the incremental extraction. Each step replaces one import
source until the monolith is deleted.
"""

from adversaries import ADVERSARIES
from gauntlet_monolith import (
    format_gauntlet_report,
    get_adversary_leaderboard,
    get_medal_leaderboard,
    run_gauntlet,
)

__all__ = [
    "ADVERSARIES",
    "format_gauntlet_report",
    "get_adversary_leaderboard",
    "get_medal_leaderboard",
    "run_gauntlet",
]
