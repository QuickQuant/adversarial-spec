"""DurableStateStore + StateTransaction (MW-002).

Crash-safe read-modify-write over `fcntl.flock` shared/exclusive locking with
a deterministic multi-artifact lock order, so recovery reads only the complete
old or new state.

Scaffolded by W0-1; implemented by W0-4.
"""

__all__: list[str] = []
