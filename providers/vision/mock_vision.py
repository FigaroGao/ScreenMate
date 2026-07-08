"""
Mock vision provider — returns canned responses without calling any API.

Replace with a real provider (OpenAI, Qwen, Gemini, etc.) by dropping a
new file into ``providers/vision/`` that subclasses
:class:`BaseVisionProvider` and registers itself.
"""

import time
from typing import Any, Optional

from providers import register_provider
from providers.base.vision import BaseVisionProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class MockVisionProvider(BaseVisionProvider):
    """Mock vision provider for development and testing.

    Always returns a successful :class:`ProviderResponse` with placeholder
    content.  Real providers should follow the same return contract.
    """

    def analyze(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Return a mock analysis of the provided image.

        Args:
            image_data: Raw image bytes (ignored in mock).
            prompt: Optional user prompt.
            **kwargs: Ignored.

        Returns:
            A :class:`ProviderResponse` with mock content.
        """
        t0 = time.perf_counter()
        logger.info(
            "MockVisionProvider.analyze: image_size=%d bytes, prompt=%s",
            len(image_data),
            prompt[:80] if prompt else "(none)",
        )

        latency_ms = (time.perf_counter() - t0) * 1000

        return ProviderResponse.ok(
            provider=self.provider_name,
            model=self.model_name,
            content=(
                "\U0001f5bc️ [Mock Vision] This is a simulated vision analysis.\n\n"
                "I see a desktop screen with various application windows.\n"
                "If this were a real vision model, I would describe the\n"
                "actual content of the screenshot here."
            ),
            latency_ms=round(latency_ms, 2),
            usage={"prompt_tokens": 150, "completion_tokens": 60},
            metadata={"image_size_bytes": len(image_data)},
        )

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-vision-v1"


# Auto-register when the module is imported
register_provider("vision", "mock", MockVisionProvider)
