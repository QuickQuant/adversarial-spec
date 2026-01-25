"""
Knowledge Service - Context7 Integration with Caching

Provides documentation lookup via Context7 MCP tools with:
- Local filesystem caching (24h TTL default)
- Soft token limits with tracking (not hard caps)
- Evidence logging for assumption verification
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class VerificationStatus(str, Enum):
    """Status of a claim verification against documentation."""
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIABLE = "unverifiable"
    PENDING = "pending"


@dataclass
class DocChunk:
    """A chunk of documentation content."""
    content: str
    token_estimate: int  # Rough estimate: len/4
    source_query: str
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class DocCacheEntry:
    """Cached documentation for a library."""
    library_id: str
    library_name: str
    fetched_at: datetime
    expires_at: datetime
    chunks: list[DocChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def total_tokens(self) -> int:
        return sum(c.token_estimate for c in self.chunks)

    def to_dict(self) -> dict:
        return {
            "library_id": self.library_id,
            "library_name": self.library_name,
            "fetched_at": self.fetched_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "chunks": [
                {
                    "content": c.content,
                    "token_estimate": c.token_estimate,
                    "source_query": c.source_query,
                    "fetched_at": c.fetched_at.isoformat(),
                }
                for c in self.chunks
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DocCacheEntry:
        return cls(
            library_id=data["library_id"],
            library_name=data["library_name"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            chunks=[
                DocChunk(
                    content=c["content"],
                    token_estimate=c["token_estimate"],
                    source_query=c["source_query"],
                    fetched_at=datetime.fromisoformat(c["fetched_at"]),
                )
                for c in data.get("chunks", [])
            ],
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvidenceItem:
    """Evidence for or against a claim."""
    claim_id: str
    claim_text: str
    source_library: str
    verification_status: VerificationStatus
    supporting_text: str  # Quote from docs
    context7_query: str  # Query used to find this
    checked_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "source_library": self.source_library,
            "verification_status": self.verification_status.value,
            "supporting_text": self.supporting_text,
            "context7_query": self.context7_query,
            "checked_at": self.checked_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EvidenceItem:
        return cls(
            claim_id=data["claim_id"],
            claim_text=data["claim_text"],
            source_library=data["source_library"],
            verification_status=VerificationStatus(data["verification_status"]),
            supporting_text=data["supporting_text"],
            context7_query=data["context7_query"],
            checked_at=datetime.fromisoformat(data["checked_at"]),
        )


@dataclass
class TokenUsageLog:
    """Tracks token usage for soft limit monitoring."""
    query: str
    library_id: str
    tokens_fetched: int
    soft_limit: int
    exceeded: bool
    timestamp: datetime = field(default_factory=datetime.now)


class KnowledgeService:
    """
    Manages documentation lookup via Context7 with caching.

    Uses soft limits with tracking - logs when limits are exceeded
    but doesn't block the operation. This allows review of whether
    limits need adjustment.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_hours: int = 24,
        soft_token_limit: int = 2000,
        context7_resolve: Callable | None = None,
        context7_query: Callable | None = None,
    ):
        """
        Initialize the knowledge service.

        Args:
            cache_dir: Where to store cached docs. Default: ~/.cache/adversarial-spec/knowledge/
            ttl_hours: Cache TTL in hours. Default: 24
            soft_token_limit: Soft limit for tokens per query. Logged but not enforced.
            context7_resolve: MCP tool function for resolve-library-id
            context7_query: MCP tool function for query-docs
        """
        self.cache_dir = cache_dir or Path.home() / ".cache" / "adversarial-spec" / "knowledge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.ttl = timedelta(hours=ttl_hours)
        self.soft_token_limit = soft_token_limit

        # MCP tool functions - injected by caller
        self._resolve_fn = context7_resolve
        self._query_fn = context7_query

        # In-memory cache for current session
        self._memory_cache: dict[str, DocCacheEntry] = {}

        # Token usage tracking
        self.token_usage_log: list[TokenUsageLog] = []

        # Evidence log for current session
        self.evidence_log: list[EvidenceItem] = []

    def _cache_path(self, library_id: str) -> Path:
        """Get the cache file path for a library."""
        # Sanitize library_id for filesystem
        safe_id = library_id.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_id}.json.gz"

    def _load_from_cache(self, library_id: str) -> DocCacheEntry | None:
        """Load a library from disk cache."""
        # Check memory cache first
        if library_id in self._memory_cache:
            entry = self._memory_cache[library_id]
            if not entry.is_expired():
                return entry
            else:
                del self._memory_cache[library_id]

        # Check disk cache
        cache_path = self._cache_path(library_id)
        if not cache_path.exists():
            return None

        try:
            with gzip.open(cache_path, "rt", encoding="utf-8") as f:
                data = json.load(f)
            entry = DocCacheEntry.from_dict(data)

            if entry.is_expired():
                cache_path.unlink()  # Clean up expired cache
                return None

            # Store in memory cache
            self._memory_cache[library_id] = entry
            return entry

        except (json.JSONDecodeError, gzip.BadGzipFile, KeyError) as e:
            logger.warning(f"Cache corruption for {library_id}: {e}. Deleting.")
            cache_path.unlink(missing_ok=True)
            return None

    def _save_to_cache(self, entry: DocCacheEntry) -> None:
        """Save a library to disk cache."""
        self._memory_cache[entry.library_id] = entry

        cache_path = self._cache_path(entry.library_id)
        with gzip.open(cache_path, "wt", encoding="utf-8") as f:
            json.dump(entry.to_dict(), f)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return len(text) // 4

    def _log_token_usage(self, query: str, library_id: str, tokens: int) -> None:
        """Log token usage for soft limit monitoring."""
        exceeded = tokens > self.soft_token_limit

        log_entry = TokenUsageLog(
            query=query,
            library_id=library_id,
            tokens_fetched=tokens,
            soft_limit=self.soft_token_limit,
            exceeded=exceeded,
        )
        self.token_usage_log.append(log_entry)

        if exceeded:
            logger.warning(
                f"Soft token limit exceeded: {tokens} > {self.soft_token_limit} "
                f"(library={library_id}, query={query[:50]}...)"
            )

    def resolve_library(self, library_name: str, user_query: str = "") -> str | None:
        """
        Resolve a library name to a Context7 library ID.

        Args:
            library_name: Name of the library (e.g., "polymarket", "@stripe/stripe-node")
            user_query: Context about what the user is trying to accomplish

        Returns:
            Library ID like "/polymarket/clob-client" or None if not found
        """
        if not self._resolve_fn:
            logger.warning("Context7 resolve function not configured")
            return None

        try:
            result = self._resolve_fn(libraryName=library_name, query=user_query)
            # Parse result to extract library ID
            # Context7 returns structured data with library matches
            if isinstance(result, dict) and "library_id" in result:
                return result["library_id"]
            elif isinstance(result, str):
                # May return the ID directly
                return result if result.startswith("/") else None
            return None
        except Exception as e:
            logger.error(f"Context7 resolve failed for {library_name}: {e}")
            return None

    def get_documentation(
        self,
        library_id: str,
        query: str,
        force_refresh: bool = False,
    ) -> list[str]:
        """
        Get documentation for a library, using cache when available.

        Args:
            library_id: Context7 library ID (e.g., "/polymarket/clob-client")
            query: What to look up in the docs
            force_refresh: Skip cache and fetch fresh

        Returns:
            List of relevant documentation chunks
        """
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._load_from_cache(library_id)
            if cached:
                # Look for existing chunk with similar query
                for chunk in cached.chunks:
                    if self._queries_similar(chunk.source_query, query):
                        return [chunk.content]

        # Fetch from Context7
        if not self._query_fn:
            logger.warning("Context7 query function not configured")
            return []

        try:
            result = self._query_fn(libraryId=library_id, query=query)

            if isinstance(result, str):
                content = result
            elif isinstance(result, dict):
                content = result.get("content", result.get("text", str(result)))
            else:
                content = str(result)

            # Track token usage (soft limit)
            tokens = self._estimate_tokens(content)
            self._log_token_usage(query, library_id, tokens)

            # Create and cache the chunk
            chunk = DocChunk(
                content=content,
                token_estimate=tokens,
                source_query=query,
            )

            # Update or create cache entry
            cached = self._load_from_cache(library_id) or DocCacheEntry(
                library_id=library_id,
                library_name=library_id.split("/")[-1] if "/" in library_id else library_id,
                fetched_at=datetime.now(),
                expires_at=datetime.now() + self.ttl,
            )
            cached.chunks.append(chunk)
            cached.expires_at = datetime.now() + self.ttl  # Refresh TTL
            self._save_to_cache(cached)

            return [content]

        except Exception as e:
            logger.error(f"Context7 query failed for {library_id}: {e}")
            return []

    def _queries_similar(self, q1: str, q2: str) -> bool:
        """Check if two queries are similar enough to reuse cached results."""
        # Simple: exact match or one contains the other
        q1_lower = q1.lower().strip()
        q2_lower = q2.lower().strip()
        return q1_lower == q2_lower or q1_lower in q2_lower or q2_lower in q1_lower

    def verify_claim(
        self,
        claim_text: str,
        library_name: str,
        verification_query: str,
    ) -> EvidenceItem:
        """
        Verify a claim against documentation.

        Args:
            claim_text: The claim to verify (e.g., "Polymarket requires nonces")
            library_name: Library to check (e.g., "polymarket")
            verification_query: Query to find relevant docs

        Returns:
            EvidenceItem with verification status
        """
        claim_id = self._make_claim_id(claim_text)

        # Resolve library
        library_id = self.resolve_library(library_name, verification_query)
        if not library_id:
            evidence = EvidenceItem(
                claim_id=claim_id,
                claim_text=claim_text,
                source_library=library_name,
                verification_status=VerificationStatus.UNVERIFIABLE,
                supporting_text=f"Could not resolve library: {library_name}",
                context7_query=verification_query,
            )
            self.evidence_log.append(evidence)
            return evidence

        # Fetch documentation
        docs = self.get_documentation(library_id, verification_query)
        if not docs:
            evidence = EvidenceItem(
                claim_id=claim_id,
                claim_text=claim_text,
                source_library=library_id,
                verification_status=VerificationStatus.UNVERIFIABLE,
                supporting_text="No documentation found for query",
                context7_query=verification_query,
            )
            self.evidence_log.append(evidence)
            return evidence

        # For now, return the docs as supporting text
        # Actual verification (VERIFIED vs REFUTED) requires LLM analysis
        evidence = EvidenceItem(
            claim_id=claim_id,
            claim_text=claim_text,
            source_library=library_id,
            verification_status=VerificationStatus.PENDING,
            supporting_text=docs[0][:2000],  # Truncate for storage
            context7_query=verification_query,
        )
        self.evidence_log.append(evidence)
        return evidence

    def _make_claim_id(self, claim_text: str) -> str:
        """Generate a stable ID for a claim."""
        h = hashlib.sha1(claim_text.encode()).hexdigest()[:8]
        return f"CLAIM-{h}"

    def get_token_usage_summary(self) -> dict:
        """Get summary of token usage for review."""
        if not self.token_usage_log:
            return {"total_fetches": 0, "total_tokens": 0, "exceeded_count": 0}

        return {
            "total_fetches": len(self.token_usage_log),
            "total_tokens": sum(log.tokens_fetched for log in self.token_usage_log),
            "exceeded_count": sum(1 for log in self.token_usage_log if log.exceeded),
            "soft_limit": self.soft_token_limit,
            "violations": [
                {
                    "query": log.query[:50],
                    "library": log.library_id,
                    "tokens": log.tokens_fetched,
                }
                for log in self.token_usage_log
                if log.exceeded
            ],
        }

    def save_evidence_log(self, path: Path) -> None:
        """Save evidence log to a file."""
        data = {
            "evidence": [e.to_dict() for e in self.evidence_log],
            "token_usage": self.get_token_usage_summary(),
            "saved_at": datetime.now().isoformat(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def clear_cache(self, library_id: str | None = None) -> int:
        """
        Clear cached documentation.

        Args:
            library_id: Specific library to clear, or None for all

        Returns:
            Number of cache entries cleared
        """
        if library_id:
            self._memory_cache.pop(library_id, None)
            path = self._cache_path(library_id)
            if path.exists():
                path.unlink()
                return 1
            return 0

        # Clear all
        count = 0
        for path in self.cache_dir.glob("*.json.gz"):
            path.unlink()
            count += 1
        self._memory_cache.clear()
        return count
