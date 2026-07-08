"""
Mock TTS provider — returns a simulated audio result without calling any API.

Replace with a real provider (OpenAI, Azure, Edge-TTS, etc.) by dropping
a new file into ``providers/tts/`` that subclasses
:class:`BaseTTSProvider` and registers itself.
"""

import time
from typing import Any

from providers import register_provider
from providers.base.tts import BaseTTSProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS provider for development and testing.

    Always returns a successful :class:`ProviderResponse` — no audio is
    actually generated.  Real providers should follow the same contract.
    """

    def synthesize(self, text: str, **kwargs: Any) -> ProviderResponse:
        """Pretend to convert text to speech.

        Args:
            text: The text to speak.
            **kwargs: Additional parameters (voice, speed) — ignored.

        Returns:
            A :class:`ProviderResponse` with mock metadata.
        """
        t0 = time.perf_counter()

        voice = kwargs.get("voice", self.voice)
        logger.info(
            "MockTTSProvider.synthesize: text_len=%d, voice=%s",
            len(text),
            voice,
        )

        word_count = len(text.split())
        estimated_ms = max(500, word_count * 250)
        latency_ms = (time.perf_counter() - t0) * 1000

        return ProviderResponse.ok(
            provider=self.provider_name,
            model=voice,
            content="/static/audio/placeholder.mp3",
            latency_ms=round(latency_ms, 2),
            metadata={
                "format": "mp3",
                "duration_ms": estimated_ms,
                "voice": voice,
                "word_count": word_count,
            },
        )

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def voice(self) -> str:
        return "mock-voice-default"


# Auto-register when the module is imported
register_provider("tts", "mock", MockTTSProvider)
