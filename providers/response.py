"""
Unified provider response for ScreenMate.

Every provider (vision, chat, TTS) MUST return a :class:`ProviderResponse`
(or subclass) so that upstream code (pipelines, routes, dashboard) can
rely on a consistent data shape regardless of which concrete provider
was invoked.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderResponse:
    """Standardised response envelope returned by every provider call.

    All fields have sensible defaults so that a provider only needs to
    set the fields that are meaningful for its domain.

    Attributes:
        success: Whether the call succeeded.
        provider: Short provider name (e.g. ``"mock"``, ``"openai"``).
        model: The model identifier used for this call.
        content: The primary output (text for vision/chat, path for TTS).
        latency_ms: Wall-clock time the call took, in milliseconds.
        usage: Token-usage or other cost metadata.
        metadata: Arbitrary extra data (image dimensions, voice name, …).
        error: Human-readable error description when ``success`` is ``False``.
    """

    success: bool = True
    provider: str = ""
    model: str = ""
    content: str = ""
    latency_ms: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def ok(
        cls,
        provider: str,
        model: str,
        content: str,
        latency_ms: float = 0.0,
        usage: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ProviderResponse":
        """Create a successful response in one call."""
        return cls(
            success=True,
            provider=provider,
            model=model,
            content=content,
            latency_ms=latency_ms,
            usage=usage or {},
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        provider: str,
        error: str,
        latency_ms: float = 0.0,
    ) -> "ProviderResponse":
        """Create a failure response in one call."""
        return cls(
            success=False,
            provider=provider,
            error=error,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict suitable for API responses."""
        return {
            "success": self.success,
            "provider": self.provider,
            "model": self.model,
            "content": self.content,
            "latency_ms": self.latency_ms,
            "usage": self.usage,
            "metadata": self.metadata,
            "error": self.error,
        }
