"""TmrRegistryWriter (MW-010).

The single persistence path for the Session TMR registry: read revision ->
validate preconditions -> write under canonical lock order -> bump revision.
A static authoring-lint rule fails any write-open call site outside the two
sole writers.

Scaffolded by W0-1; implemented by W0-13.
"""

__all__: list[str] = []
