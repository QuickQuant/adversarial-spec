"""
Discovery Agent - Pre-Debate Documentation Fetching

Runs BEFORE the constructive debate to:
1. Extract external service/library names from the user's prompt
2. Fetch high-level documentation via Context7
3. Build a "priming context" that grounds the debate in reality

This prevents assumptions by giving models actual documentation
rather than letting them pattern-match from training data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredService:
    """An external service/library identified in the spec."""
    name: str
    confidence: float  # 0.0 to 1.0
    context: str  # Surrounding text where it was found
    doc_fetched: bool = False
    doc_summary: str = ""


@dataclass
class DiscoveryResult:
    """Result of the discovery phase."""
    services: list[DiscoveredService] = field(default_factory=list)
    priming_context: str = ""
    token_usage: dict[str, Any] = field(default_factory=dict)
    discovery_time_ms: int = 0
    errors: list[str] = field(default_factory=list)


class DiscoveryAgent:
    """
    Extracts external services from spec text and fetches their documentation.

    This runs BEFORE the constructive debate phase to prevent the models
    from making assumptions about how external systems work.
    """

    # Common service/library patterns to detect
    SERVICE_PATTERNS = [
        # SDK patterns: @org/package, org-package
        (r"@[\w-]+/[\w-]+", 0.9),  # @polymarket/clob-client
        (r"[\w]+-sdk", 0.8),  # stripe-sdk

        # API mentions
        (r"\b(\w+)\s+API\b", 0.7),  # "Polymarket API"
        (r"\bAPI\s+for\s+(\w+)", 0.7),  # "API for Stripe"

        # Integration keywords
        (r"integrat(?:e|ing|ion)\s+(?:with\s+)?(\w+)", 0.6),

        # Common services (high confidence when mentioned)
        (r"\b(Polymarket|Kalshi|Stripe|Twilio|SendGrid|AWS|GCP|Azure|Firebase|Supabase|Convex|Prisma|MongoDB|PostgreSQL|Redis|Kafka|RabbitMQ)\b", 0.95),
    ]

    # Patterns that look like services but aren't
    FALSE_POSITIVE_PATTERNS = [
        r"^(the|a|an|this|that|our|their|your)$",
        r"^(API|SDK|HTTP|REST|GraphQL|WebSocket)$",  # Generic terms
        r"^\d+$",  # Numbers
    ]

    def __init__(self, knowledge_service=None):
        """
        Initialize the discovery agent.

        Args:
            knowledge_service: KnowledgeService instance for doc fetching.
                              If None, discovery still works but won't fetch docs.
        """
        self.knowledge_service = knowledge_service

    def extract_services(self, text: str) -> list[DiscoveredService]:
        """
        Extract external service names from text.

        Uses regex patterns and heuristics. Not perfect, but catches
        the common cases that lead to false assumptions.
        """
        services: dict[str, DiscoveredService] = {}

        for pattern, confidence in self.SERVICE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract the service name
                if match.lastindex:
                    name = match.group(1)
                else:
                    name = match.group(0)

                name = name.strip()

                # Skip false positives
                if self._is_false_positive(name):
                    continue

                # Get surrounding context (50 chars each side)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]

                # Use highest confidence if seen multiple times
                if name.lower() in services:
                    existing = services[name.lower()]
                    if confidence > existing.confidence:
                        existing.confidence = confidence
                        existing.context = context
                else:
                    services[name.lower()] = DiscoveredService(
                        name=name,
                        confidence=confidence,
                        context=context,
                    )

        # Sort by confidence descending
        return sorted(services.values(), key=lambda s: -s.confidence)

    def _is_false_positive(self, name: str) -> bool:
        """Check if a name is a false positive."""
        if len(name) < 2:
            return True

        for pattern in self.FALSE_POSITIVE_PATTERNS:
            if re.match(pattern, name, re.IGNORECASE):
                return True

        return False

    def fetch_service_docs(
        self,
        service: DiscoveredService,
        query: str = "overview architecture how it works",
    ) -> bool:
        """
        Fetch documentation for a discovered service.

        Args:
            service: The service to look up
            query: What to ask about the service

        Returns:
            True if docs were fetched successfully
        """
        if not self.knowledge_service:
            logger.warning("No knowledge service configured, skipping doc fetch")
            return False

        try:
            # Try to resolve the library
            library_id = self.knowledge_service.resolve_library(
                service.name,
                query,
            )

            if not library_id:
                service.doc_summary = f"Could not find documentation for {service.name}"
                return False

            # Fetch docs
            docs = self.knowledge_service.get_documentation(
                library_id,
                query,
            )

            if docs:
                service.doc_fetched = True
                service.doc_summary = docs[0][:1500]  # Truncate for context
                return True
            else:
                service.doc_summary = f"No documentation found for {library_id}"
                return False

        except Exception as e:
            logger.error(f"Error fetching docs for {service.name}: {e}")
            service.doc_summary = f"Error: {e}"
            return False

    def build_priming_context(
        self,
        services: list[DiscoveredService],
        include_unfetched: bool = True,
    ) -> str:
        """
        Build markdown context to inject into the debate.

        This gives models ground truth about external services
        instead of letting them assume.
        """
        if not services:
            return ""

        lines = [
            "## External Service Documentation (Ground Truth)",
            "",
            "**IMPORTANT**: The following documentation was fetched from official sources.",
            "Do NOT make assumptions about these services - refer to this documentation.",
            "",
        ]

        fetched = [s for s in services if s.doc_fetched]
        unfetched = [s for s in services if not s.doc_fetched]

        if fetched:
            for service in fetched:
                lines.append(f"### {service.name}")
                lines.append("")
                lines.append(service.doc_summary)
                lines.append("")

        if include_unfetched and unfetched:
            lines.append("### Services Without Documentation")
            lines.append("")
            lines.append("The following services were mentioned but documentation could not be fetched.")
            lines.append("**Treat all claims about these services as UNVERIFIED.**")
            lines.append("")
            for service in unfetched:
                lines.append(f"- **{service.name}**: {service.doc_summary or 'Not found'}")
            lines.append("")

        return "\n".join(lines)

    def discover(
        self,
        spec_text: str,
        min_confidence: float = 0.6,
        max_services: int = 5,
    ) -> DiscoveryResult:
        """
        Run the full discovery pipeline.

        Args:
            spec_text: The specification or user prompt
            min_confidence: Minimum confidence to include a service
            max_services: Maximum services to fetch docs for (to avoid token explosion)

        Returns:
            DiscoveryResult with services, context, and metadata
        """
        start_time = datetime.now()
        result = DiscoveryResult()

        # Extract services
        all_services = self.extract_services(spec_text)
        result.services = [s for s in all_services if s.confidence >= min_confidence]

        # Limit to top N for doc fetching
        services_to_fetch = result.services[:max_services]

        # Fetch docs for each
        for service in services_to_fetch:
            try:
                self.fetch_service_docs(service)
            except Exception as e:
                result.errors.append(f"Failed to fetch {service.name}: {e}")

        # Build priming context
        result.priming_context = self.build_priming_context(result.services)

        # Capture token usage if knowledge service is available
        if self.knowledge_service:
            result.token_usage = self.knowledge_service.get_token_usage_summary()

        result.discovery_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result


def run_discovery(
    spec_text: str,
    knowledge_service=None,
    min_confidence: float = 0.6,
    max_services: int = 5,
) -> DiscoveryResult:
    """
    Convenience function to run discovery.

    Args:
        spec_text: The specification text
        knowledge_service: Optional KnowledgeService for doc fetching
        min_confidence: Minimum confidence threshold
        max_services: Maximum services to fetch

    Returns:
        DiscoveryResult with priming context
    """
    agent = DiscoveryAgent(knowledge_service=knowledge_service)
    return agent.discover(
        spec_text,
        min_confidence=min_confidence,
        max_services=max_services,
    )
