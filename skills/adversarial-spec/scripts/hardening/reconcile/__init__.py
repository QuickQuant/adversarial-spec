"""Explicit in-process registry of reconciliation adapters.

Adapters are package-qualified callables registered here by name. There is no
dynamic plugin discovery and no subprocess plugin protocol (closes OQ-A1) --
a reconciliation path that is not listed in this registry does not exist.

Scaffolded by W0-1; adapters land with their owning tasks.
"""

__all__: list[str] = []
