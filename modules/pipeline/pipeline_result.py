"""
Standardised pipeline result.

Every pipeline returns a :class:`PipelineResult` so that routes can
render responses without knowing which pipeline was executed.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from providers.response import ProviderResponse


@dataclass
class PipelineResult:
    """Result envelope returned by every pipeline execution.

    Attributes:
        success: Whether the pipeline completed successfully.
        message: Human-readable summary (shown in toasts / status badges).
        data: Arbitrary payload — rendered as JSON in API responses.
        error: Error description when ``success`` is ``False``.
        processing_time_ms: Total wall-clock time for the pipeline run.
        vision_response: The :class:`ProviderResponse` from the vision step
            (if applicable).
        tts_response: The :class:`ProviderResponse` from the TTS step
            (if applicable).
        chat_response: The :class:`ProviderResponse` from the chat step
            (if applicable).
    """

    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    processing_time_ms: float = 0.0

    vision_response: Optional[ProviderResponse] = None
    tts_response: Optional[ProviderResponse] = None
    chat_response: Optional[ProviderResponse] = None

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def ok(
        cls,
        message: str = "Completed",
        data: Optional[dict[str, Any]] = None,
        processing_time_ms: float = 0.0,
        **kwargs: Any,
    ) -> "PipelineResult":
        """Create a successful result."""
        return cls(
            success=True,
            message=message,
            data=data or {},
            processing_time_ms=processing_time_ms,
            **kwargs,
        )

    @classmethod
    def fail(cls, error: str, **kwargs: Any) -> "PipelineResult":
        """Create a failure result."""
        return cls(
            success=False,
            message="Pipeline failed",
            error=error,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dict for API responses."""
        result: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
            "processing_time_ms": self.processing_time_ms,
        }
        if self.error:
            result["error"] = self.error
        if self.data:
            result.update(self.data)
        if self.vision_response:
            result["vision"] = self.vision_response.to_dict()
        if self.tts_response:
            result["tts"] = self.tts_response.to_dict()
        if self.chat_response:
            result["chat"] = self.chat_response.to_dict()
        return result
