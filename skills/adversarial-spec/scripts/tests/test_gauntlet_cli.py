"""Regression tests for the standalone gauntlet CLI surface."""

from io import StringIO
from unittest.mock import patch

import pytest


def test_standalone_cli_rejects_show_manifest_flag():
    """The secondary CLI must not duplicate debate.py's manifest viewer."""
    from gauntlet.cli import main

    with patch("sys.argv", ["gauntlet", "--show-manifest", "abc123"]):
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                main()

    assert exc_info.value.code == 2
    assert "unrecognized arguments" in mock_stderr.getvalue()
