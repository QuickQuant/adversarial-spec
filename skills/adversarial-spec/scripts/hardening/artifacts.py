"""StrictArtifactCodec (MW-001).

Strict envelope encode/decode over RFC 8785 JCS canonical bytes.

Owns the `local-derived` / `authority-signed` envelope profiles and the
`content_hash` rule (SHA-256 over JCS with `content_hash`, `generated_at`,
and `authority.signature` omitted) -- a semantic hash, not a byte-immutability
claim.

Scaffolded by W0-1; implemented by W0-2.
"""

__all__: list[str] = []
