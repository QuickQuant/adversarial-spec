"""DurableOperationJournal (MW-011).

Runtime-local intent journal -- imports no transport. The operation identity,
contract id, behavior fingerprint and canonical request hash are journaled and
fsynced BEFORE dispatch, so a crash is resolved by record presence rather than
by guessing what the remote saw.

Scaffolded by W0-1; implemented by W0-10.
"""

__all__: list[str] = []
