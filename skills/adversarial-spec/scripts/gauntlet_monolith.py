"""Backwards-compatibility shim — all code has moved to the gauntlet/ package.

This file exists solely so that any external code doing
``from gauntlet_monolith import ...`` continues to work.
New code should import from the gauntlet package directly.
"""

from gauntlet.cli import main  # noqa: F401
from gauntlet.orchestrator import run_gauntlet  # noqa: F401

if __name__ == "__main__":
    main()
