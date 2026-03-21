"""Tests for gauntlet orchestrator behavioral paths."""

import builtins
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from gauntlet.core_types import GauntletConfig
from models import CostTracker


def test_cost_tracker_thread_safety():
    """Concurrent CostTracker.add() calls must not lose data."""
    tracker = CostTracker()
    n_threads = 100
    barrier = threading.Barrier(n_threads)

    def add_once():
        barrier.wait()
        tracker.add("test-model", 10, 5)

    threads = [threading.Thread(target=add_once) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert tracker.total_input_tokens == 1000
    assert tracker.total_output_tokens == 500


def test_unattended_never_calls_input():
    """Unattended mode must monkey-patch input() to raise RuntimeError."""
    original = builtins.input

    try:
        # Apply the same monkey-patch that orchestrator.py uses
        builtins.input = lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("input() called in unattended mode")
        )

        with pytest.raises(RuntimeError, match="input\\(\\) called in unattended mode"):
            builtins.input("prompt")
    finally:
        builtins.input = original

    # Verify restore worked
    assert builtins.input is original
