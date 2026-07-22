"""Hardening package: durable state, artifact integrity, and authority contracts.

Component boundaries follow the target architecture's package tree
(`target-architecture.md` § "Package and Component Boundaries"). Two rules
constrain everything in here:

1. **No upward import from `gauntlet`.** Existing gauntlet persistence supplies
   tested implementation ideas, but copying them upward would make this package
   depend on an application (no app -> app).
2. **Hermetic split is an import boundary.** Local bootstrap modules must not
   import or instantiate remote transports; only `remote_authority` owns those.

Modules land one per task (W0-2 .. W0-13); this scaffold declares the boundary
so wave-0 tasks cannot invent a different file layout.
"""

__all__: list[str] = []
