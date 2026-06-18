"""Adversarial spec development scripts."""

__version__ = "1.0.0"

import sys
from pathlib import Path
_scripts_dir = str(Path(__file__).parent.resolve())
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

