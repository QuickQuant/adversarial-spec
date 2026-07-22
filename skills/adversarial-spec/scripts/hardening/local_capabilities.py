"""LocalCapabilityVerifier (MW-006).

Offline signature/version/freshness verification of cached capability
attestations, plus a monotonic authority-time watermark that is never
decremented -- a wall-clock rollback cannot extend authorization.

Scaffolded by W0-1; implemented by W0-11.
"""

__all__: list[str] = []
