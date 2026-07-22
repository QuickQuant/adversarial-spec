"""RemoteAuthorityClient (MW-007).

The ONLY module permitted to hold remote transports. Snapshot upload/finalize,
prepare, commit and status reconciliation over injected transports; never
dispatches a recoverable mutation without a durable MW-011 intent.

Scaffolded by W0-1; implemented by W0-12.
"""

__all__: list[str] = []
